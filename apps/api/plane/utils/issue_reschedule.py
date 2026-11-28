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

A project can switch the offer off (``Project.is_reschedule_offer_enabled``): a change to one of its work items that
breaks a relation is then refused as it was before the offer existed, also when the request carries
``shift_dependents``. The project of the work item that is changed decides, not those of its dependents.

Each dependent (and each sub-work item) that moves gets an activity entry naming the work item whose change moved
it, passed to the activity task as ``shifted_after`` beside the requested data (which a client can fill, so it never
carries the cause).

The offer warns about the deadline: each shifted work item whose new ``finish_date`` passes its due date
(``target_date``, which shifting never changes) carries the overrun in working days of its own project. A work item
that was late already is warned about only when the shift makes it later still, with the overrun it had before.

**Parents.** A parent counts in its dependencies with its effective span, its own dates widened by those of its
sub-work items (``issue_effective_span``), when it is the predecessor. So a sub-work item that moves (by hand or as
a dependent) can push what depends on its parent, and the shift follows that too.

**Sub-work items** can follow a parent that moves, by hand or as a dependent, but only when the person says so: the
offer lists them, ticked by default, and the request that confirms it carries ``move_sub_items`` (true or false).
Each one moves by the working days the parent's start moved and keeps its own length; completed, cancelled and
non-editable ones, and those the request itself changes, stay where they are. Moved sub-work items take their own
dependents (and sub-work items) along. A client asks for sub-work items to be offered with ``offer_sub_items``:
without it a change that breaks no relation is saved as it is and sub-work items never move, as before they could.
With the offer switched off for the project nothing moves along, sub-work items included.
"""

import json
from collections import deque
from datetime import timedelta
from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import Issue, Project, ProjectMember
from plane.utils.issue_effective_span import EffectiveSpans
from plane.utils.issue_relation_constraints import RELATION_DATE_CONFLICT, _as_date, dependent_side
from plane.utils.work_item_duration import (
    add_working_days,
    count_working_days,
    effective_finish,
    effective_start,
    shift_working_days,
    subtract_working_days,
)
from plane.utils.work_item_edit_rule import can_change_work_items, unchangeable_issue_ids
from plane.utils.issue_timeline_relation_validation import (
    _is_satisfied,
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

# what a moved work item is in a plan: something that depends on a moved work item, or below one
DEPENDENT = "dependent"
SUB_ITEM = "sub_item"

# the request flags: confirm the shift of dependents, ask for sub-work items to be offered, answer that offer
SHIFT_DEPENDENTS = "shift_dependents"
OFFER_SUB_ITEMS = "offer_sub_items"
MOVE_SUB_ITEMS = "move_sub_items"

# what an offer of sub-work items says when no relation is broken
SUB_ITEMS_OFFER = {"error": "The sub-work items of this work item can move with it.", "error_code": None}


def _flag(data, key) -> Optional[bool]:
    """A boolean request flag: True, False, or None when it is not there (or not a boolean)."""
    value = data.get(key) if hasattr(data, "get") else None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1"):
            return True
        if value.lower() in ("false", "0"):
            return False
    return None


def is_shift_confirmed(data) -> bool:
    return _flag(data, SHIFT_DEPENDENTS) is True


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
        return "finish_date", shift_working_days(effective_finish(pred_finish, weekend_days), lag, weekend_days)
    if relation_type == "start_before_finish" and pred_start is not None:
        return "finish_date", shift_working_days(effective_start(pred_start, weekend_days), lag, weekend_days)
    return None


def deadline_overrun(finish_date, target_date, weekend_days=()) -> int:
    """
    Working days by which work that finishes on ``finish_date`` passes its due date ``target_date``; 0 when it does
    not, or when either date is missing.

    The working days after the due date up to the finish are counted, so a finish on a weekend day right after
    the due date is not late, and a due date on a weekend day is met by work that ends on the working day before.
    """
    finish_date, target_date = _as_date(finish_date), _as_date(target_date)
    if finish_date is None or target_date is None or finish_date <= target_date:
        return 0
    return count_working_days(target_date + timedelta(days=1), finish_date, weekend_days)


def deadline_warning(issue, new_finish_date) -> dict:
    """
    ``deadline_overrun_days`` (and ``previous_deadline_overrun_days``) for a work item moved to ``new_finish_date``.

    The overrun is given only when the shift makes the work item pass its due date by more than before (otherwise
    None); the previous overrun only beside it, and only when the work item was late already.
    """
    weekend_days = weekend_days_of(issue)
    before = deadline_overrun(issue.finish_date, issue.target_date, weekend_days)
    after = deadline_overrun(new_finish_date, issue.target_date, weekend_days)
    if after <= before:
        return {"deadline_overrun_days": None, "previous_deadline_overrun_days": None}
    return {"deadline_overrun_days": after, "previous_deadline_overrun_days": before or None}


def _working_days_between(earlier, later, weekend_days) -> int:
    """Working days to get from one working day to another; negative when ``later`` is before ``earlier``."""
    if later >= earlier:
        return count_working_days(earlier, later, weekend_days) - 1
    return -(count_working_days(later, earlier, weekend_days) - 1)


def start_offset(before, after, weekend_days=()) -> int:
    """Working days a start moved from ``before`` to ``after`` (negative: earlier); 0 when either is missing."""
    before, after = _as_date(before), _as_date(after)
    if before is None or after is None:
        return 0
    return _working_days_between(
        effective_start(before, weekend_days), effective_start(after, weekend_days), weekend_days
    )


def follow(dates, offset, weekend_days=()):
    """
    The ``(start_date, finish_date)`` of a sub-work item that moves ``offset`` working days with its parent, keeping
    the working days it lasts. One with only a finish date moves that; one without dates does not move (None).
    """
    start, finish = _as_date(dates.get("start_date")), _as_date(dates.get("finish_date"))
    dates = {"start_date": start, "finish_date": finish}
    if start is not None:
        moved_start = shift_working_days(effective_start(start, weekend_days), offset, weekend_days)
        return _move_to(dates, "start_date", moved_start, weekend_days)
    if finish is not None:
        moved_finish = shift_working_days(effective_finish(finish, weekend_days), offset, weekend_days)
        return _move_to(dates, "finish_date", moved_finish, weekend_days)
    return None


def _move_to(dates, field_name, earliest, weekend_days):
    """
    The ``(start_date, finish_date)`` of a work item whose ``field_name`` has to move to ``earliest``: the other date
    follows so that it keeps the number of working days it lasted.
    """
    start, finish = dates["start_date"], dates["finish_date"]
    length = max(count_working_days(start, finish, weekend_days), 1) if start and finish else None
    if field_name == "start_date":
        return earliest, (add_working_days(earliest, length, weekend_days) if length else finish)
    return (subtract_working_days(earliest, length, weekend_days) if length else start), earliest


@dataclass
class ReschedulePlan:
    # work item id -> its work item and proposed dates, for the work items that move
    # each entry also names the work item of the request whose change moved it ("cause_id"), and whether it moves
    # as a dependent or as a sub-work item following its parent ("kind", DEPENDENT when left out)
    shifted: dict = field(default_factory=dict)

    def updates(self):
        return [
            {"id": issue_id, "start_date": entry["start_date"], "finish_date": entry["finish_date"]}
            for issue_id, entry in self.shifted.items()
        ]

    def entries(self, kind):
        return [entry for entry in self.shifted.values() if entry.get("kind", DEPENDENT) == kind]

    @property
    def dependents(self):
        return self.entries(DEPENDENT)

    @property
    def sub_items(self):
        return self.entries(SUB_ITEM)

    def payload(self, original_error: dict, with_sub_items: Optional["ReschedulePlan"] = None) -> dict:
        """
        The offer: ``shifts`` are the dependents that move when the sub-work items stay. With ``with_sub_items`` (the
        plan in which they follow their parents) it also lists those (``sub_items``) and what moves then
        (``shifts_with_sub_items``); without it they are empty and the same as ``shifts``.
        """
        shifts = [_shift_payload(entry) for entry in self.dependents]
        return {
            "error": original_error.get("error", "These dates conflict with existing dependencies."),
            "error_code": RELATION_RESCHEDULE_AVAILABLE,
            "original_error_code": original_error.get("error_code"),
            "shifts": shifts,
            "sub_items": [_shift_payload(entry) for entry in with_sub_items.sub_items] if with_sub_items else [],
            "shifts_with_sub_items": (
                [_shift_payload(entry) for entry in with_sub_items.dependents] if with_sub_items else shifts
            ),
        }


def _shift_payload(entry) -> dict:
    issue = entry["issue"]
    return {
        "id": str(issue.id),
        "project_id": str(issue.project_id),
        "sequence_id": issue.sequence_id,
        "ref": issue_display_ref(issue),
        "name": issue.name,
        "start_date": _iso(issue.start_date),
        "finish_date": _iso(issue.finish_date),
        "new_start_date": _iso(entry["start_date"]),
        "new_finish_date": _iso(entry["finish_date"]),
        "target_date": _iso(issue.target_date),
        **deadline_warning(issue, entry["finish_date"]),
    }


def _iso(value):
    value = _as_date(value)
    return value.isoformat() if value else None


def _load_issues(ids, objects):
    """Put the work items of ``ids`` that are not loaded yet into ``objects`` (id -> work item)."""
    missing = [issue_id for issue_id in ids if str(issue_id) not in objects]
    if missing:
        for issue in Issue.issue_objects.select_related("state", "project").filter(pk__in=missing):
            objects[str(issue.id)] = issue


def _editable_ids(actor, issues, member_projects) -> set:
    """The ids of ``issues`` the person may change: a member of their project, and not kept out by the assignee rule.

    ``member_projects`` caches project id -> whether the person is a member who may edit there.
    """
    by_project = {}
    for issue in issues:
        by_project.setdefault(issue.project_id, []).append(str(issue.id))
    unknown = {project_id for project_id in by_project if project_id not in member_projects}
    if unknown:
        editable = set(
            ProjectMember.objects.filter(
                member=actor, is_active=True, role__gte=MEMBER_ROLE, project_id__in=unknown
            ).values_list("project_id", flat=True)
        )
        for project_id in unknown:
            member_projects[project_id] = project_id in editable
    allowed = set()
    for project_id, ids in by_project.items():
        if member_projects[project_id]:
            allowed.update(set(ids) - unchangeable_issue_ids(actor, project_id, ids))
    return allowed


def _comes_too_early(issue, dates, current, spans) -> bool:
    """Whether ``dates`` put ``issue`` before something it depends on (with the dates planned so far)."""
    for relation_type, related, lag in _iter_timeline_constraints(issue):
        if dependent_side(relation_type) != "issue":
            continue
        related_dates = current.get(str(related.id)) or {
            "start_date": _as_date(related.start_date),
            "finish_date": _as_date(related.finish_date),
        }
        if not _is_satisfied(relation_type, issue, dates, related, related_dates, lag, spans):
            return True
    return False


def _stored_dates(issue) -> dict:
    return {"start_date": _as_date(issue.start_date), "finish_date": _as_date(issue.finish_date)}


def plan_reschedule(
    proposed: dict, issues_by_id: dict, actor, with_sub_items: bool = False
) -> Optional[ReschedulePlan]:
    """Plan the shifts that make the dates in ``proposed`` (work item id -> start/finish dates) satisfy every rule.

    With ``with_sub_items`` the sub-work items of every work item that moves follow it (see the module docstring).
    Returns None when nothing has to move, when the dates cannot be made to satisfy every rule, or when a shift is not
    allowed.
    """
    current = {
        str(issue_id): {
            "start_date": _as_date(dates.get("start_date")),
            "finish_date": _as_date(dates.get("finish_date")),
        }
        for issue_id, dates in proposed.items()
    }
    moved_by_request = set(current)
    objects = {str(issue_id): issues_by_id[str(issue_id)] for issue_id in current if str(issue_id) in issues_by_id}
    spans = EffectiveSpans()
    for issue_id, dates in current.items():
        spans.set_dates(issue_id, dates["start_date"], dates["finish_date"])
    # work item id -> DEPENDENT or SUB_ITEM, for the work items that move besides those of the request
    moved = {}
    # work item id -> the work item of the request its move goes back to; the request's own items are their own cause
    causes = {issue_id: issue_id for issue_id in current}
    member_projects = {}

    def place(issue_id, dates, kind, cause):
        current[issue_id] = dates
        spans.set_dates(issue_id, dates["start_date"], dates["finish_date"])
        moved.setdefault(issue_id, kind)
        causes[issue_id] = cause

    def take_sub_items_along(parent_id):
        """Move the sub-work items of a work item that moved by as many working days as its start; their ids."""
        parent = objects[parent_id]
        offset = start_offset(parent.start_date, current[parent_id]["start_date"], weekend_days_of(parent))
        if not offset:
            return []
        descendant_ids = spans.descendants(parent)
        _load_issues(descendant_ids, objects)
        candidates = [
            objects[str(issue_id)]
            for issue_id in descendant_ids
            if str(issue_id) in objects
            and str(issue_id) not in moved_by_request
            and getattr(objects[str(issue_id)].state, "group", None) not in NOT_MOVED_GROUPS
        ]
        editable = _editable_ids(actor, candidates, member_projects)
        followed = []
        for child in sorted(candidates, key=lambda issue: (issue.sequence_id or 0, str(issue.id))):
            child_id = str(child.id)
            if child_id not in editable:
                continue
            new_dates = follow(_stored_dates(child), offset, weekend_days_of(child))
            if new_dates is None:
                continue
            new_dates = {"start_date": new_dates[0], "finish_date": new_dates[1]}
            if child_id in current:
                # already moved as far by something it depends on, or by another parent: the later place wins
                field_name = "start_date" if new_dates["start_date"] is not None else "finish_date"
                planned = current[child_id][field_name]
                if planned is not None and planned >= new_dates[field_name]:
                    continue
            # moving earlier with its parent must not put it before something it depends on: then it stays
            if offset < 0 and _comes_too_early(child, new_dates, current, spans):
                continue
            place(child_id, new_dates, SUB_ITEM, causes[parent_id])
            followed.append(child_id)
        return followed

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
        has_moved = predecessor_id in current
        if with_sub_items and has_moved:
            queue.extend(take_sub_items_along(predecessor_id))
            if len(moved) > MAX_SHIFTED_ISSUES:
                return None
        # as a predecessor a parent counts with the dates of its sub-work items too
        dates = spans.span(predecessor, current.get(predecessor_id) or _stored_dates(predecessor))
        for relation_type, successor, lag in _iter_timeline_constraints(predecessor):
            weekend_days = weekend_days_of(successor)
            requirement = _successor_requirement(
                relation_type, dates["start_date"], dates["finish_date"], lag, weekend_days
            )
            if requirement is None:
                continue
            successor_id = str(successor.id)
            field_name, earliest = requirement
            successor_dates = current.get(successor_id) or _stored_dates(successor)
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
            start, finish = _move_to(successor_dates, field_name, earliest, weekend_days)
            place(successor_id, {"start_date": start, "finish_date": finish}, DEPENDENT, causes[predecessor_id])
            if len(moved) > MAX_SHIFTED_ISSUES:
                return None
            queue.append(successor_id)
        # a work item that moved changes the span of the parents above it: what depends on them is checked again
        if has_moved and getattr(predecessor, "parent_id", None) is not None:
            ancestor_ids = [str(ancestor_id) for ancestor_id in spans.ancestors(predecessor)]
            _load_issues(ancestor_ids, objects)
            for ancestor_id in ancestor_ids:
                if ancestor_id in objects:
                    causes.setdefault(ancestor_id, causes[predecessor_id])
                    queue.append(ancestor_id)

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
                "finish_date": current[issue_id]["finish_date"],
                "cause_id": causes[issue_id],
                "kind": kind,
            }
            for issue_id, kind in moved.items()
        }
    )

    # what is left must satisfy every rule, including those of the work items the request changes itself
    batch = [
        {"id": issue_id, "start_date": dates["start_date"], "finish_date": dates["finish_date"]}
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
        for field_name in ("start_date", "finish_date"):
            before, after = _iso(getattr(issue, field_name)), _iso(entry[field_name])
            if before != after:
                changes[field_name] = (before, after)
        if not changes:
            continue
        cause_id = entry.get("cause_id")
        type(issue).objects.filter(pk=issue.pk).update(
            start_date=entry["start_date"], finish_date=entry["finish_date"], updated_at=now, updated_by_id=actor_id
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
                    # the work item whose change moved this one, named in the entry (never taken from a payload)
                    "shifted_after": cause_id,
                }
            )

    def announce():
        for activity in activities:
            issue_activity.delay(**activity)

    transaction.on_commit(announce)


def _dates_after(issue, update):
    """The start and finish date a work item would have after ``update``; a key left out leaves that date alone."""
    return {
        "start_date": update["start_date"] if "start_date" in update else issue.start_date,
        "finish_date": update["finish_date"] if "finish_date" in update else issue.finish_date,
    }


def is_offer_enabled(project_ids) -> bool:
    """Whether every one of these projects lets a date change be offered with other work items moved along."""
    project_ids = {project_id for project_id in project_ids if project_id}
    if not project_ids:
        return True
    return not Project.objects.filter(pk__in=project_ids, is_reschedule_offer_enabled=False).exists()


@dataclass
class RescheduleDecision:
    """What a date change does: save with ``plan`` applied (None: nothing else moves), or answer 400 with ``offer``
    (the person has to confirm first) or with ``refusal`` (it cannot be saved)."""

    plan: Optional[ReschedulePlan] = None
    offer: Optional[dict] = None
    refusal: Optional[dict] = None


def decide_reschedule(proposed, issues_by_id, actor, timeline_error, data) -> RescheduleDecision:
    """
    Decide what a change of the dates in ``proposed`` (work item id -> start/finish dates) does, given the relation
    error it raised (``timeline_error``, or None) and the flags of the request (``data``):

    * no flag and no error: saved as it is, nothing else moves (and nothing is queried);
    * an error the offer cannot fix, an offer switched off, or a plan that cannot be made: refused with the error;
    * ``move_sub_items`` (true or false): the answer to the offer. The plan with or without the sub-work items is
      applied; when dependents move in it, ``shift_dependents`` has to be there too, else it is offered again;
    * ``shift_dependents`` alone: the dependents are shifted and the sub-work items stay, as for a client that does
      not know about them;
    * ``offer_sub_items``: offered when anything would move, the dependents or the sub-work items;
    * otherwise an error is offered with the dependents shifted, as before sub-work items could follow.
    """
    if timeline_error and timeline_error.get("error_code") != RELATION_DATE_CONFLICT:
        return RescheduleDecision(refusal=timeline_error)
    answer = _flag(data, MOVE_SUB_ITEMS)
    confirmed = is_shift_confirmed(data)
    asked = _flag(data, OFFER_SUB_ITEMS) is True
    if not timeline_error and answer is not True and not asked:
        return RescheduleDecision()
    if not proposed or not is_offer_enabled(issues_by_id[issue_id].project_id for issue_id in proposed):
        # with the offer switched off nothing moves along: neither dependents nor sub-work items
        return RescheduleDecision(refusal=timeline_error)

    base = None
    if timeline_error:
        base = plan_reschedule(proposed, issues_by_id, actor)
        if base is None:
            return RescheduleDecision(refusal=timeline_error)
    with_sub_items = None
    if answer is True or (asked and answer is None and not confirmed):
        with_sub_items = plan_reschedule(proposed, issues_by_id, actor, with_sub_items=True)
        if with_sub_items is not None and not with_sub_items.sub_items:
            with_sub_items = None

    def offer():
        return RescheduleDecision(
            offer=(base or ReschedulePlan()).payload(timeline_error or SUB_ITEMS_OFFER, with_sub_items=with_sub_items)
        )

    if answer is not None:
        # sub-work items that can no longer follow (something changed since the offer) stay where they are
        chosen = with_sub_items if answer and with_sub_items is not None else base
        if chosen is not None and chosen.dependents and not confirmed:
            return offer()
        return RescheduleDecision(plan=chosen)
    if confirmed:
        return RescheduleDecision(plan=base)
    if base is None and with_sub_items is None:
        return RescheduleDecision()
    return offer()


def decide_for_issue_update(issue, attrs, actor, timeline_error, data) -> RescheduleDecision:
    """``decide_reschedule`` for an update of one work item with serializer ``attrs`` and request ``data``."""
    if "start_date" not in attrs and "finish_date" not in attrs:
        return RescheduleDecision(refusal=timeline_error)
    return decide_reschedule(
        {str(issue.id): _dates_after(issue, attrs)}, {str(issue.id): issue}, actor, timeline_error, data
    )


def decide_for_batch(updates, issues_by_id, actor, timeline_error, data) -> RescheduleDecision:
    """``decide_reschedule`` for a batch of date updates (a timeline drag)."""
    proposed = {}
    for update in updates:
        issue = issues_by_id.get(str(update.get("id")))
        if issue is not None:
            proposed[str(issue.id)] = _dates_after(issue, update)
    return decide_reschedule(proposed, issues_by_id, actor, timeline_error, data)
