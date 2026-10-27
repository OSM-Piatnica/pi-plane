# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the project copy tasks of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

# Python imports
import logging
from datetime import timedelta

# Third party imports
from celery import shared_task

# Django imports
from django.db.models import Q
from django.utils import timezone

# Module imports
from plane.db.models import ProjectCopyJob
from plane.utils import project_copy_work_items

log = logging.getLogger(__name__)

# How often a failing copy is handed back to a worker before it is given up on
MAX_COPY_ATTEMPTS = 3


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def copy_project_work_items(self, job_id: str) -> int:
    """Copy a duplicated project's work items, resuming if an earlier run died.

    Deliberately not `autoretry_for`: that re-enters the body without going through the lease, so two
    workers could believe they own the same job. A failure here releases the lease and either
    redispatches with backoff or terminalises, and the sweeper below covers the cases where the worker
    never got far enough to do either.
    """
    job = ProjectCopyJob.objects.filter(pk=job_id).select_related("target_project").first()
    if job is None or job.is_terminal:
        return 0

    claimed = project_copy_work_items.claim(job, task_id=self.request.id or "")
    if claimed is None:
        # Somebody else holds a live lease, or it finished while this message sat in the queue.
        # Redelivery is expected; doing nothing is correct.
        return 0

    claimed.target_project = job.target_project

    if claimed.source_project_id is None:
        return _finish_copy(claimed, ProjectCopyJob.Status.FAILED, reason="source_project_deleted")

    try:
        tally = project_copy_work_items.copy_work_items(claimed)
    except Exception as error:  # noqa: BLE001 - recorded, then retried or terminalised
        log.exception("project copy job %s failed", job_id)
        claimed.refresh_from_db()
        if claimed.attempt_count < MAX_COPY_ATTEMPTS:
            _release_lease(claimed)
            copy_project_work_items.apply_async(args=[str(claimed.id)], countdown=min(60, 2**claimed.attempt_count))
            return 0
        claimed.errors = (claimed.errors or []) + [{"error": str(error)[:500]}]
        return _finish_copy(claimed, ProjectCopyJob.Status.FAILED, reason="copy_failed")

    claimed.counts = tally.counts
    claimed.skipped = tally.skipped
    status = ProjectCopyJob.Status.COMPLETED_WITH_ERRORS if claimed.errors else ProjectCopyJob.Status.COMPLETED
    return _finish_copy(claimed, status)


def _release_lease(job) -> None:
    job.lease_token = None
    job.lease_expires_at = None
    job.status = ProjectCopyJob.Status.QUEUED
    job.save(update_fields=["lease_token", "lease_expires_at", "status", "updated_at"])


def _finish_copy(job, status, reason: str = "") -> int:
    """Terminalise, releasing the lease -- which the check constraint requires."""
    job.status = status
    job.reason = reason
    job.completed_at = timezone.now()
    job.lease_token = None
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "reason",
            "completed_at",
            "lease_token",
            "lease_expires_at",
            "counts",
            "skipped",
            "errors",
            "stage",
            "copied",
            "updated_at",
        ]
    )
    return job.copied


@shared_task
def reclaim_stalled_project_copies() -> int:
    """Redispatch copies whose worker died, and ones the broker never delivered.

    This single sweep closes both holes: a worker killed mid-copy leaves a `processing` job with an
    expired lease, and a broker outage at dispatch leaves a `queued` job nobody was ever told about.
    Resuming is safe because every pass skips what it already wrote.
    """
    now = timezone.now()
    stalled = ProjectCopyJob.objects.filter(
        Q(status=ProjectCopyJob.Status.PROCESSING, lease_expires_at__lt=now)
        | Q(status=ProjectCopyJob.Status.QUEUED, created_at__lt=now - timedelta(minutes=5))
    ).values_list("id", flat=True)[:50]

    dispatched = 0
    for job_id in list(stalled):
        copy_project_work_items.apply_async(args=[str(job_id)])
        dispatched += 1
    return dispatched
