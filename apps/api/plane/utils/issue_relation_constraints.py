# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, datetime, timedelta

HAS_STARTED_GROUPS = frozenset({"started", "completed"})
COMPLETED_GROUPS = frozenset({"completed"})
SKIP_STATUS_GROUPS = frozenset({"cancelled"})

RELATION_DATE_CONFLICT = "relation_date_conflict"
RELATION_STATUS_CONFLICT = "relation_status_conflict"

# Relation types carrying date semantics, from the perspective of the issue being edited.
TIMELINE_RELATION_TYPES = frozenset(
    {
        "blocked_by",
        "blocking",
        "start_before",
        "start_after",
        "finish_before",
        "finish_after",
        "start_before_finish",
        "finish_after_start",
    }
)

# Largest lag (or lead, when negative) a relation may carry, in calendar days
MAX_LAG_DAYS = 3650

# Of those, the ones actually stored in the database. The remaining three are inferred by
# swapping `issue` and `related_issue`.
STORED_TIMELINE_RELATION_TYPES = ["blocked_by", "start_before", "finish_before", "start_before_finish"]


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"Unsupported date value: {type(value)!r}")


def _plus_days(value, days):
    return value + timedelta(days=days) if value is not None else None


def is_start_before_satisfied(issue_start, related_start, lag=0) -> bool:
    """Start-to-start: the related work item starts at least ``lag`` days after this one (0 = on or after)."""
    left = _plus_days(_as_date(issue_start), lag)
    right = _as_date(related_start)
    if left is None or right is None:
        return True
    return left <= right


def is_start_after_satisfied(issue_start, related_start, lag=0) -> bool:
    return is_start_before_satisfied(related_start, issue_start, lag)


def is_finish_before_satisfied(issue_finish, related_finish, lag=0) -> bool:
    """Finish-to-finish: the related work item finishes at least ``lag`` days after this one."""
    left = _plus_days(_as_date(issue_finish), lag)
    right = _as_date(related_finish)
    if left is None or right is None:
        return True
    return left <= right


def is_finish_after_satisfied(issue_finish, related_finish, lag=0) -> bool:
    return is_finish_before_satisfied(related_finish, issue_finish, lag)


def is_start_before_finish_satisfied(issue_start, related_finish, lag=0) -> bool:
    """Start-to-finish: the related work item cannot finish before ``lag`` days after this one has started."""
    left = _plus_days(_as_date(issue_start), lag)
    right = _as_date(related_finish)
    if left is None or right is None:
        return True
    return left <= right


def is_finish_after_start_satisfied(issue_finish, related_start, lag=0) -> bool:
    return is_start_before_finish_satisfied(related_start, issue_finish, lag)


def is_blocked_by_satisfied(issue_start, blocker_finish, lag=0) -> bool:
    """
    Finish-to-start: the blocker has to be done before the blocked work item starts, ``lag`` days apart.

    Both dates are inclusive calendar days, so a blocker finishing on the day the blocked item
    starts still overlaps it: with no lag the blocked item starts the day *after* the blocker
    finishes. A lag of 2 asks for two free days in between; a lead of -1 lets them share a day.
    """
    start = _as_date(issue_start)
    finish = _plus_days(_as_date(blocker_finish), lag)
    if start is None or finish is None:
        return True
    return finish < start


def is_timeline_relation_satisfied(relation_type, issue_dates, related_dates, lag=0) -> bool:
    issue_start = (issue_dates or {}).get("start_date")
    issue_finish = (issue_dates or {}).get("target_date")
    related_start = (related_dates or {}).get("start_date")
    related_finish = (related_dates or {}).get("target_date")

    if relation_type == "blocked_by":
        return is_blocked_by_satisfied(issue_start, related_finish, lag)
    if relation_type == "blocking":
        return is_blocked_by_satisfied(related_start, issue_finish, lag)
    if relation_type == "start_before":
        return is_start_before_satisfied(issue_start, related_start, lag)
    if relation_type == "start_after":
        return is_start_after_satisfied(issue_start, related_start, lag)
    if relation_type == "finish_before":
        return is_finish_before_satisfied(issue_finish, related_finish, lag)
    if relation_type == "finish_after":
        return is_finish_after_satisfied(issue_finish, related_finish, lag)
    if relation_type == "start_before_finish":
        return is_start_before_finish_satisfied(issue_start, related_finish, lag)
    if relation_type == "finish_after_start":
        return is_finish_after_start_satisfied(issue_finish, related_start, lag)

    raise ValueError(f"Unsupported timeline relation type: {relation_type}")


def is_status_transition_allowed(relation_type, issue_group, related_group) -> bool:
    """
    Status rules from the perspective of the issue being updated.
    Cancelled transitions are always allowed.
    """
    if issue_group in SKIP_STATUS_GROUPS or related_group in SKIP_STATUS_GROUPS:
        return True

    if relation_type == "start_after":
        if issue_group in HAS_STARTED_GROUPS:
            return related_group in HAS_STARTED_GROUPS
        return True

    if relation_type == "finish_after":
        if issue_group in COMPLETED_GROUPS:
            return related_group in COMPLETED_GROUPS
        return True

    if relation_type == "finish_after_start":
        # cannot be completed before the related work item has started
        if issue_group in COMPLETED_GROUPS:
            return related_group in HAS_STARTED_GROUPS
        return True

    # start_before / finish_before constrain the related issue (seen as after from its side)
    return True


def date_violation_message(relation_type, issue_ref: str, related_ref: str) -> str:
    messages = {
        "blocked_by": (
            f"Cannot update dates: {issue_ref} cannot start before {related_ref} finishes (blocked by relation)."
        ),
        "blocking": (f"Cannot update dates: {issue_ref} must finish before {related_ref} starts (blocking relation)."),
        "start_before": (
            f"Cannot update dates: {issue_ref} must start on or before {related_ref} (starts before relation)."
        ),
        "start_after": (f"Cannot update dates: {issue_ref} cannot start before {related_ref} (starts after relation)."),
        "finish_before": (
            f"Cannot update dates: {issue_ref} must finish on or before {related_ref} (finishes before relation)."
        ),
        "finish_after": (
            f"Cannot update dates: {issue_ref} cannot finish before {related_ref} (finishes after relation)."
        ),
        "start_before_finish": (
            f"Cannot update dates: {issue_ref} must start on or before {related_ref} finishes "
            f"(starts before finish relation)."
        ),
        "finish_after_start": (
            f"Cannot update dates: {issue_ref} cannot finish before {related_ref} starts "
            f"(finishes after start relation)."
        ),
    }
    return messages[relation_type]


def status_violation_message(relation_type, issue_ref: str, related_ref: str) -> str:
    if relation_type == "start_after":
        return (
            f"Cannot change status: {issue_ref} cannot start until {related_ref} has started (starts after relation)."
        )
    if relation_type == "finish_after":
        return (
            f"Cannot change status: {issue_ref} cannot be completed until {related_ref} is completed "
            f"(finishes after relation)."
        )
    if relation_type == "finish_after_start":
        return (
            f"Cannot change status: {issue_ref} cannot be completed until {related_ref} has started "
            f"(finishes after start relation)."
        )
    return f"Cannot change status due to timeline relation between {issue_ref} and {related_ref}."


def date_violation_error(relation_type, issue_ref: str, related_ref: str, lag: int = 0) -> dict:
    """
    Error payload for a broken date constraint.

    `error` carries a ready English sentence so any existing consumer keeps working, while the
    remaining keys let the web app rebuild the same sentence in the user's own language.
    """
    return {
        "error": date_violation_message(relation_type, issue_ref, related_ref)
        + (f" The relation has a lag of {lag} days." if lag else ""),
        "error_code": RELATION_DATE_CONFLICT,
        "relation_type": relation_type,
        "issue_ref": issue_ref,
        "related_ref": related_ref,
        "lag_days": lag,
    }


def status_violation_error(relation_type, issue_ref: str, related_ref: str) -> dict:
    return {
        "error": status_violation_message(relation_type, issue_ref, related_ref),
        "error_code": RELATION_STATUS_CONFLICT,
        "relation_type": relation_type,
        "issue_ref": issue_ref,
        "related_ref": related_ref,
    }
