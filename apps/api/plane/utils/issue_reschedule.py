# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Moving the work items that depend on a work item whose dates are changed.

A date change that breaks a timeline relation is refused (``issue_timeline_relation_validation``). When the break is
only that something that has to come *after* the changed work item would now come too early, the work items
downstream can be shifted later instead, keeping the working days they last. That is offered to the person, who
confirms it by sending the request again with ``shift_dependents``; the API then applies the shifts together with
the change.

Every timeline rule has the form "the successor's date is at least a function of the predecessor's date and the lag",
so shifting a successor later can only break rules where it is itself the predecessor: the shift is followed down the
chain. Work items that are completed or cancelled, that the person may not edit, or that the request itself changes
are never moved; then nothing is offered and the change stays refused.
"""

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import ProjectMember
from plane.utils.issue_relation_constraints import _as_date
from plane.utils.work_item_duration import (
    add_working_days,
    count_working_days,
    effective_finish,
    effective_start,
    shift_working_days,
    subtract_working_days,
)
from plane.utils.work_item_edit_rule import can_change_work_items
from plane.utils.issue_timeline_relation_validation import (
    _iter_timeline_constraints,
    issue_display_ref,
    validate_issue_dates_batch,
    weekend_days_of,
)

RELATION_RESCHEDULE_AVAILABLE = "relation_reschedule_available"

# A chain longer than this is not followed: it is a loop of rules across relation types, or far too long to offer
MAX_STEPS = 500
MAX_SHIFTED_ISSUES = 100

MEMBER_ROLE = 15
NOT_MOVED_GROUPS = ("completed", "cancelled")


def is_shift_confirmed(data) -> bool:
    value = data.get("shift_dependents") if hasattr(data, "get") else None
    return value is True or (isinstance(value, str) and value.lower() in ("true", "1"))


class RescheduleOffered(APIException):
    """Answers 400 with the payload as it is, like ``ParentReopenRequired``: a client looks for ``error_code``."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, payload: dict):
        self.detail = payload


def _successor_requirement(relation_type, pred_start, pred_finish, lag, weekend_days=()):
    """
    ``(field, earliest)`` the successor's date has to reach, for a rule where the changed item is the predecessor.

    Counted in working days with the successor's ``weekend_days``, the same way the rule is checked
    (``issue_relation_constraints``): a start or finish on a weekend day counts as the nearest working day.
    """
    if relation_type == "blocking" and pred_finish is not None:
        return "start_date", shift_working_days(effective_finish(pred_finish, weekend_days), 1 + lag, weekend_days)
    if relation_type == "start_before" and pred_start is not None:
        return "start_date", shift_working_days(effective_start(pred_start, weekend_days), lag, weekend_days)
    if relation_type == "finish_before" and pred_finish is not None:
        return "target_date", shift_working_days(effective_finish(pred_finish, weekend_days), lag, weekend_days)
    if relation_type == "start_before_finish" and pred_start is not None:
        return "target_date", shift_working_days(effective_start(pred_start, weekend_days), lag, weekend_days)
    return None


def _move_to(dates, field_name, earliest, weekend_days):
    """
    The ``(start_date, target_date)`` of a work item whose ``field_name`` has to move to ``earliest``: the other date
    follows so that it keeps the number of working days it lasted.
    """
    start, target = dates["start_date"], dates["target_date"]
    length = max(count_working_days(start, target, weekend_days), 1) if start and target else None
    if field_name == "start_date":
        return earliest, (add_working_days(earliest, length, weekend_days) if length else target)
    return (subtract_working_days(earliest, length, weekend_days) if length else start), earliest


@dataclass
class ReschedulePlan:
    # work item id -> its work item and proposed dates, for the dependents that move
    shifted: dict = field(default_factory=dict)

    def updates(self):
        return [
            {"id": issue_id, "start_date": entry["start_date"], "target_date": entry["target_date"]}
            for issue_id, entry in self.shifted.items()
        ]

    def payload(self, original_error: dict) -> dict:
        shifts = []
        for entry in self.shifted.values():
            issue = entry["issue"]
            shifts.append(
                {
                    "id": str(issue.id),
                    "project_id": str(issue.project_id),
                    "sequence_id": issue.sequence_id,
                    "ref": issue_display_ref(issue),
                    "name": issue.name,
                    "start_date": _iso(issue.start_date),
                    "target_date": _iso(issue.target_date),
                    "new_start_date": _iso(entry["start_date"]),
                    "new_target_date": _iso(entry["target_date"]),
                }
            )
        return {
            "error": original_error.get("error", "These dates conflict with existing dependencies."),
            "error_code": RELATION_RESCHEDULE_AVAILABLE,
            "original_error_code": original_error.get("error_code"),
            "shifts": shifts,
        }


def _iso(value):
    value = _as_date(value)
    return value.isoformat() if value else None


def plan_reschedule(proposed: dict, issues_by_id: dict, actor) -> Optional[ReschedulePlan]:
    """Plan the shifts that make the dates in ``proposed`` (work item id -> start/target dates) satisfy every rule.

    Returns None when they cannot be made to, or when a shift is not allowed (see the module docstring).
    """
    current = {
        str(issue_id): {
            "start_date": _as_date(dates.get("start_date")),
            "target_date": _as_date(dates.get("target_date")),
        }
        for issue_id, dates in proposed.items()
    }
    moved_by_request = set(current)
    objects = {str(issue_id): issues_by_id[str(issue_id)] for issue_id in current if str(issue_id) in issues_by_id}
    moved = {}

    queue = deque(current)
    steps = 0
    while queue:
        predecessor_id = queue.popleft()
        steps += 1
        if steps > MAX_STEPS:
            return None
        predecessor = objects.get(predecessor_id)
        if predecessor is None:
            continue
        dates = current[predecessor_id]
        for relation_type, successor, lag in _iter_timeline_constraints(predecessor):
            weekend_days = weekend_days_of(successor)
            requirement = _successor_requirement(
                relation_type, dates["start_date"], dates["target_date"], lag, weekend_days
            )
            if requirement is None:
                continue
            successor_id = str(successor.id)
            field_name, earliest = requirement
            successor_dates = current.setdefault(
                successor_id,
                {"start_date": _as_date(successor.start_date), "target_date": _as_date(successor.target_date)},
            )
            objects.setdefault(successor_id, successor)
            value = successor_dates[field_name]
            if value is None:
                continue
            # a date on a weekend day stands for the working day next to it, as when the rule is checked
            as_worked = (
                effective_start(value, weekend_days)
                if field_name == "start_date"
                else effective_finish(value, weekend_days)
            )
            if as_worked >= earliest:
                continue
            if successor_id in moved_by_request or getattr(successor.state, "group", None) in NOT_MOVED_GROUPS:
                return None
            moved[successor_id] = True
            successor_dates["start_date"], successor_dates["target_date"] = _move_to(
                successor_dates, field_name, earliest, weekend_days
            )
            if len(moved) > MAX_SHIFTED_ISSUES:
                return None
            queue.append(successor_id)

    if not moved:
        return None

    # the person has to be allowed to edit every work item that moves
    moving = [objects[issue_id] for issue_id in moved]
    editable_projects = set(
        ProjectMember.objects.filter(
            member=actor,
            is_active=True,
            role__gte=MEMBER_ROLE,
            project_id__in={issue.project_id for issue in moving},
        ).values_list("project_id", flat=True)
    )
    if any(issue.project_id not in editable_projects for issue in moving):
        return None
    # and, where a project restricts changes to assignees, the dependents it lets them change
    if not can_change_work_items(actor, moving):
        return None

    plan = ReschedulePlan(
        shifted={
            issue_id: {
                "issue": objects[issue_id],
                "start_date": current[issue_id]["start_date"],
                "target_date": current[issue_id]["target_date"],
            }
            for issue_id in moved
        }
    )

    # what is left must satisfy every rule, including those of the work items the request changes itself
    batch = [
        {"id": issue_id, "start_date": dates["start_date"], "target_date": dates["target_date"]}
        for issue_id, dates in current.items()
        if issue_id in moved_by_request
    ] + plan.updates()
    if validate_issue_dates_batch(batch, objects):
        return None
    return plan


def apply_shifts(plan: ReschedulePlan, actor_id) -> None:
    """Write the shifted dates of the dependents, with an activity entry per changed date."""
    now = timezone.now()
    epoch = int(now.timestamp())
    activities = []
    for issue_id, entry in plan.shifted.items():
        issue = entry["issue"]
        changes = {}
        for field_name in ("start_date", "target_date"):
            before, after = _iso(getattr(issue, field_name)), _iso(entry[field_name])
            if before != after:
                changes[field_name] = (before, after)
        if not changes:
            continue
        type(issue).objects.filter(pk=issue.pk).update(
            start_date=entry["start_date"], target_date=entry["target_date"], updated_at=now, updated_by_id=actor_id
        )
        for field_name, (before, after) in changes.items():
            activities.append(
                {
                    "type": "issue.activity.updated",
                    "requested_data": json.dumps({field_name: after}),
                    "current_instance": json.dumps({field_name: before}),
                    "issue_id": issue_id,
                    "actor_id": str(actor_id),
                    "project_id": str(issue.project_id),
                    "epoch": epoch,
                    # a dependent moved along is not the person's doing: no subscription to it
                    "subscriber": False,
                }
            )

    def announce():
        for activity in activities:
            issue_activity.delay(**activity)

    transaction.on_commit(announce)


def _dates_after(issue, update):
    """The start and target date a work item would have after ``update``; a key left out leaves that date alone."""
    return {
        "start_date": update["start_date"] if "start_date" in update else issue.start_date,
        "target_date": update["target_date"] if "target_date" in update else issue.target_date,
    }


def plan_for_issue_update(issue, attrs, actor, timeline_error) -> Optional[ReschedulePlan]:
    """The plan for a single work item's update that ``timeline_error`` refused, if shifting dependents fixes it."""
    from plane.utils.issue_relation_constraints import RELATION_DATE_CONFLICT

    if not timeline_error or timeline_error.get("error_code") != RELATION_DATE_CONFLICT:
        return None
    if "start_date" not in attrs and "target_date" not in attrs:
        return None
    return plan_reschedule({str(issue.id): _dates_after(issue, attrs)}, {str(issue.id): issue}, actor)


def plan_for_batch(updates, issues_by_id, actor, timeline_error) -> Optional[ReschedulePlan]:
    """The plan for a batch of date updates (a timeline drag) that ``timeline_error`` refused."""
    from plane.utils.issue_relation_constraints import RELATION_DATE_CONFLICT

    if not timeline_error or timeline_error.get("error_code") != RELATION_DATE_CONFLICT:
        return None
    proposed = {}
    for update in updates:
        issue = issues_by_id.get(str(update.get("id")))
        if issue is not None:
            proposed[str(issue.id)] = _dates_after(issue, update)
    return plan_reschedule(proposed, issues_by_id, actor) if proposed else None
