# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from celery import shared_task

# Module imports
from plane.utils.exception_logger import log_exception
from plane.utils.work_item_duration_sync import recompute_project_work_item_durations


@shared_task
def recompute_project_durations(project_id):
    """Recalculate a project's work item durations after its weekend days changed."""
    try:
        return recompute_project_work_item_durations(project_id)
    except Exception as error:
        log_exception(error)
        return None
