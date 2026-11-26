# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Baselines of a project: saving the plan, and comparing the current dates with a saved plan.

A baseline remembers the start, finish and due date of every work item that had at least one of them when the
baseline was saved. The **variance** of a work item is how far its schedule moved since: its start (``start_date``) and
its finish (``finish_date``, the end of the timeline bar), in working days of the project
(``plane.utils.work_item_duration``), positive when the date is later than planned, negative when it is earlier. The
due date (``target_date``) is a deadline, not part of the schedule: the saved one is answered next to the current one,
so a moved deadline can be shown, but it has no variance.

A start on a weekend day counts as the first working day after it, a finish on a weekend day as the last working day
before it, like everywhere else. So moving a finish from a Friday to the Saturday after it is no change,
and from a Friday to the Monday after it is one day.
"""

# Django imports
from django.db import transaction
from django.db.models import Q

# Module imports
from plane.db.models import BaselineItem, Issue, Project, ProjectBaseline
from plane.db.models.baseline import MAX_BASELINES_PER_PROJECT
from plane.utils.work_item_duration import count_working_days, effective_finish, effective_start

# the dates a baseline remembers
BASELINE_DATE_FIELDS = ("start_date", "finish_date", "target_date")
# the schedule, whose moves count as variance, with the way a weekend day is read for each
SCHEDULE_DATE_FIELDS = (("start_date", effective_start), ("finish_date", effective_finish))

CAPTURE_BATCH_SIZE = 1000


class BaselineLimitReached(Exception):
    """The project already has as many baselines as it may keep."""


def working_day_difference(planned, current, weekend_days=(), effective=effective_finish):
    """Working days from ``planned`` to ``current``: positive when ``current`` is later; None when either is missing."""
    if planned is None or current is None:
        return None
    planned, current = effective(planned, weekend_days), effective(current, weekend_days)
    # both are working days now: the working days passed on the way, the day of arrival included
    if current >= planned:
        return count_working_days(planned, current, weekend_days) - 1
    return 1 - count_working_days(current, planned, weekend_days)


def _iso(value):
    return value.isoformat() if value is not None else None


def compute_variance(baseline_items, current_items, weekend_days=()):
    """Compare the current dates of work items with the ones a baseline remembers.

    :param baseline_items: ``{work item id: {"start_date", "finish_date", "target_date"}}`` from the baseline
    :param current_items: the work items as they are now, dicts with ``id`` and the same three dates
    :return: ``(items, summary)``. ``items`` has one entry per current work item that has a date now or had one in the
        baseline; a work item the baseline does not know has ``in_baseline: False`` and no baseline dates. Work items
        that are in the baseline but not among ``current_items`` (deleted, archived, hidden from the reader) are left
        out. ``summary`` compares the latest finish then and now.
    """
    items = {}
    baseline_end = None
    current_end = None
    for current in current_items:
        planned = baseline_items.get(current["id"])
        if planned is None and not any(current[field] for field in BASELINE_DATE_FIELDS):
            continue
        entry = {"in_baseline": planned is not None}
        for field in BASELINE_DATE_FIELDS:
            entry[f"baseline_{field}"] = _iso(planned[field] if planned else None)
            entry[field] = _iso(current[field])
        for field, effective in SCHEDULE_DATE_FIELDS:
            planned_day = planned[field] if planned else None
            entry[f"{field}_variance"] = working_day_difference(planned_day, current[field], weekend_days, effective)
        items[str(current["id"])] = entry

        finish = current["finish_date"]
        if finish is not None and (current_end is None or finish > current_end):
            current_end = finish
        planned_finish = planned["finish_date"] if planned else None
        if planned_finish is not None and (baseline_end is None or planned_finish > baseline_end):
            baseline_end = planned_finish

    summary = {
        "baseline_end": _iso(baseline_end),
        "current_end": _iso(current_end),
        "end_variance": working_day_difference(baseline_end, current_end, weekend_days),
    }
    return items, summary


def capture_baseline(project_id, name, description, actor_id):
    """Save the current plan of a project as a new baseline, which becomes the active one.

    Every work item of the project that is not deleted, archived, a draft or in triage and has a start, finish or due
    date is stored; work items without any date have nothing to compare later and are left out. One query reads the
    work items and the rows are written in bulk, all in one transaction. The project row is locked meanwhile, so two
    people saving at once cannot both end up active or pass the limit together.

    :raises BaselineLimitReached: when the project already keeps ``MAX_BASELINES_PER_PROJECT`` baselines
    """
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        baselines = ProjectBaseline.objects.filter(project_id=project.id)
        if baselines.count() >= MAX_BASELINES_PER_PROJECT:
            raise BaselineLimitReached()
        baselines.filter(is_active=True).update(is_active=False)

        baseline = ProjectBaseline(project=project, name=name, description=description, is_active=True)
        baseline.save(created_by_id=actor_id)

        rows = (
            Issue.issue_objects.filter(project_id=project.id)
            .filter(Q(start_date__isnull=False) | Q(finish_date__isnull=False) | Q(target_date__isnull=False))
            .values_list("id", "start_date", "finish_date", "target_date", "state__group", "completed_at")
        )
        items = [
            BaselineItem(
                baseline=baseline,
                issue_id=issue_id,
                project_id=project.id,
                workspace_id=project.workspace_id,
                start_date=start_date,
                finish_date=finish_date,
                target_date=target_date,
                state_group=state_group or "",
                completed_at=completed_at,
                created_by_id=actor_id,
            )
            for issue_id, start_date, finish_date, target_date, state_group, completed_at in rows
        ]
        BaselineItem.objects.bulk_create(items, batch_size=CAPTURE_BATCH_SIZE)

        baseline.item_count = len(items)
        baseline.save(update_fields=["item_count"], disable_auto_set_user=True)
    return baseline


def set_active_baseline(baseline, is_active):
    """Make a baseline the active one of its project (the others stop being active), or stop it being active."""
    with transaction.atomic():
        Project.objects.select_for_update().get(pk=baseline.project_id)
        if is_active:
            ProjectBaseline.objects.filter(project_id=baseline.project_id, is_active=True).exclude(
                pk=baseline.pk
            ).update(is_active=False)
        ProjectBaseline.objects.filter(pk=baseline.pk).update(is_active=is_active)
    baseline.is_active = is_active
    return baseline
