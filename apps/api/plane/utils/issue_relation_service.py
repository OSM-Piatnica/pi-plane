# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rules shared by the app and the public API when work items are related to each other."""

from plane.db.models import IssueRelation
from plane.utils.issue_relation_constraints import MAX_LAG_DAYS, TIMELINE_RELATION_TYPES
from plane.utils.issue_relation_mapper import get_actual_relation
from plane.utils.issue_relation_types import FORWARD_RELATIONS, is_mirrored, is_symmetric
from plane.utils.issue_timeline_relation_validation import issue_display_ref

RELATION_SELF = "relation_self"
RELATION_CYCLE = "relation_cycle"

# A chain longer than this, or reaching more work items than this, is not walked any further: the check then
# answers "no cycle" instead of loading an unbounded part of the workspace.
MAX_CHAIN_DEPTH = 100
MAX_CHAIN_ISSUES = 10000


def relation_ends(issue_id, other_id, relation_type):
    """The ``(issue, related_issue)`` pair of the row stored for ``issue_id <relation_type> other_id``."""
    if is_mirrored(relation_type):
        return other_id, issue_id
    return issue_id, other_id


def creates_cycle(stored_type, source_id, related_id, workspace_id):
    """Whether adding ``source -> related`` of this stored type closes a loop: ``related`` already leads to ``source``.

    Only directed types can loop (``blocked_by``, ``caused_by``, ...); ``relates_to`` and ``duplicate`` read the same
    from both sides.
    """
    if stored_type not in FORWARD_RELATIONS:
        return False

    visited = {str(related_id)}
    frontier = {related_id}
    for _ in range(MAX_CHAIN_DEPTH):
        if not frontier:
            return False
        reached = set(
            IssueRelation.objects.filter(
                workspace_id=workspace_id,
                relation_type=stored_type,
                issue_id__in=frontier,
                deleted_at__isnull=True,
            ).values_list("related_issue_id", flat=True)
        )
        if str(source_id) in {str(item) for item in reached}:
            return True
        frontier = {item for item in reached if str(item) not in visited}
        visited |= {str(item) for item in frontier}
        if len(visited) > MAX_CHAIN_ISSUES:
            return False
    return False


def validate_new_relation(current_issue, related_issue, relation_type):
    """An error payload when ``current_issue <relation_type> related_issue`` must not be created, else None."""
    current_ref = issue_display_ref(current_issue)
    related_ref = issue_display_ref(related_issue)

    if current_issue.id == related_issue.id:
        return {
            "error": f"{current_ref} cannot be related to itself.",
            "error_code": RELATION_SELF,
            "relation_type": relation_type,
            "issue_ref": current_ref,
            "related_ref": related_ref,
        }

    source, related = relation_ends(current_issue.id, related_issue.id, relation_type)
    stored_type = get_actual_relation(relation_type)
    if creates_cycle(stored_type, source, related, current_issue.workspace_id):
        return {
            "error": f"{current_ref} {relation_type.replace('_', ' ')} {related_ref} would create a loop of relations.",
            "error_code": RELATION_CYCLE,
            "relation_type": relation_type,
            "issue_ref": current_ref,
            "related_ref": related_ref,
        }
    return None


def existing_symmetric_pairs(relation_type, issue_id, other_ids):
    """Of ``other_ids``, those already related to ``issue_id`` by this symmetric type, from either side."""
    if not is_symmetric(relation_type):
        return set()
    rows = (
        IssueRelation.objects.filter(relation_type=relation_type, deleted_at__isnull=True)
        .filter(issue_id=issue_id, related_issue_id__in=other_ids)
        .values_list("related_issue_id", flat=True)
    )
    reverse = IssueRelation.objects.filter(
        relation_type=relation_type, deleted_at__isnull=True, related_issue_id=issue_id, issue_id__in=other_ids
    ).values_list("issue_id", flat=True)
    return {str(item) for item in rows} | {str(item) for item in reverse}


def parse_lag(value, relation_type):
    """``(lag_days, error)`` for the ``lag_days`` of a request: ``(None, None)`` when it was not sent."""
    if value is None or value == "":
        return None, None
    if relation_type not in TIMELINE_RELATION_TYPES:
        return None, {"error": "A lag only applies to blocking, starts and finishes relations."}
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        return None, {"error": "lag_days must be a whole number of days."}
    try:
        lag = int(value)
    except (TypeError, ValueError):
        return None, {"error": "lag_days must be a whole number of days."}
    if abs(lag) > MAX_LAG_DAYS:
        return None, {"error": f"lag_days must be between -{MAX_LAG_DAYS} and {MAX_LAG_DAYS}."}
    return lag, None


def set_lag(issue_id, others, relation_type, lag):
    """Give the rows ``issue_id <relation_type> other`` the lag, for relations that exist already."""
    stored_type = get_actual_relation(relation_type)
    for other in others:
        source, related = relation_ends(issue_id, other, relation_type)
        IssueRelation.objects.filter(
            issue_id=source, related_issue_id=related, relation_type=stored_type, deleted_at__isnull=True
        ).exclude(lag_days=lag).update(lag_days=lag)


def existing_relation_others(issue_id, others, relation_type):
    """Of ``others``, those that already have this exact relation to ``issue_id`` (so a repeat adds nothing)."""
    stored_type = get_actual_relation(relation_type)
    found = set()
    for other in others:
        source, related = relation_ends(issue_id, other, relation_type)
        if IssueRelation.objects.filter(
            issue_id=source, related_issue_id=related, relation_type=stored_type, deleted_at__isnull=True
        ).exists():
            found.add(str(other))
    return found
