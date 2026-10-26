# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bringing the stored durations of a project's work items in line with its weekend days.

A duration counts working days, so when a project changes which days are off, the same dates last a different number
of working days. The dates stay as they are and the durations follow them.
"""

from plane.db.models import Issue, Project
from plane.utils.work_item_duration import WORK_ITEM_DURATION_MIN, calculate_work_item_duration

BATCH_SIZE = 1000


def recompute_project_work_item_durations(project_id):
    """Recalculate the duration of every work item of the project that has both dates; return how many changed."""
    project = Project.objects.filter(pk=project_id).only("id", "weekend_days").first()
    if project is None:
        return 0

    changed = 0
    batch = []
    queryset = Issue.objects.filter(project_id=project.id, start_date__isnull=False, target_date__isnull=False).only(
        "id", "start_date", "target_date", "duration"
    )
    for issue in queryset.iterator(chunk_size=BATCH_SIZE):
        duration = calculate_work_item_duration(issue.start_date, issue.target_date, project.weekend_days)
        # A range ordered backwards has no meaningful duration; leave it for whoever fixes the dates
        if duration is None or duration < WORK_ITEM_DURATION_MIN or duration == issue.duration:
            continue
        issue.duration = duration
        batch.append(issue)
        if len(batch) >= BATCH_SIZE:
            Issue.objects.bulk_update(batch, ["duration"])
            changed += len(batch)
            batch = []
    if batch:
        Issue.objects.bulk_update(batch, ["duration"])
        changed += len(batch)
    return changed
