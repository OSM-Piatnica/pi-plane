# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
RACI warnings of a project (SPEC-02, "Walidacja"): gaps in the roles and the dependencies. They never block a save.

Only open work items count (not completed, cancelled, archived, draft or in triage), and not the review steps of an
acceptance, which belong to their acceptance item:

* ``no_responsible``: a work item without a responsible department;
* ``milestone_without_approver``: a milestone (work item type of kind milestone) without an approving department;
* ``department_without_members``: a department with a role on an open work item that has nobody in the project who
  would be told (no member, no member who is in the project, or switched off);
* ``no_predecessor``: a top-level work item without a predecessor, except the ones that start the project (the
  earliest start date among the open top-level work items);
* ``no_successor``: a top-level work item nothing depends on, except the ones with a due date (``target_date``) and
  the ones that end the project (the latest planned finish, ``finish_date``).

The two dependency checks are made only in a project that uses timeline relations at all; without any, every work
item would be listed. Predecessors and successors in other projects count. Sub-items are left out of them, as their
parent carries the dependencies.
"""

from collections import defaultdict

from django.db.models import Q

from plane.db.models import GroupKind, Issue, IssueRaci, IssueRelation, ProjectMember, StateGroup, UserGroup
from plane.utils.departments import department_memberships
from plane.utils.issue_relation_constraints import STORED_TIMELINE_RELATION_TYPES

# How many work items of each kind the answer names; the counts are always complete
MAX_LISTED = 200

NO_RESPONSIBLE = "no_responsible"
MILESTONE_WITHOUT_APPROVER = "milestone_without_approver"
NO_PREDECESSOR = "no_predecessor"
NO_SUCCESSOR = "no_successor"
ITEM_WARNINGS = (NO_RESPONSIBLE, MILESTONE_WITHOUT_APPROVER, NO_PREDECESSOR, NO_SUCCESSOR)

# Why a department tells nobody
INACTIVE = "inactive"
NO_MEMBERS = "no_members"
NO_PROJECT_MEMBERS = "no_project_members"


def predecessor_edges(relations):
    """``(predecessor, successor)`` for stored relations ``(issue id, related issue id, type)``: ``blocked_by`` names
    the predecessor second, the other timeline types first."""
    edges = []
    for issue_id, related_id, relation_type in relations:
        if relation_type == "blocked_by":
            edges.append((related_id, issue_id))
        elif relation_type in STORED_TIMELINE_RELATION_TYPES:
            edges.append((issue_id, related_id))
    return edges


def item_warnings(items, roles, edges):
    """
    The work item warnings, ``{kind: [item id]}`` in the order of ``items``.

    ``items``: dicts with ``id``, ``parent_id``, ``kind`` (type kind or None), ``start_date``, ``finish_date``,
    ``target_date``, open work items only. ``roles``: ``{item id: {role}}``. ``edges``: ``(predecessor, successor)``.
    """
    found = {kind: [] for kind in ITEM_WARNINGS}
    for item in items:
        item_roles = roles.get(item["id"], set())
        if "responsible" not in item_roles:
            found[NO_RESPONSIBLE].append(item["id"])
        if item.get("kind") == "milestone" and "approver" not in item_roles:
            found[MILESTONE_WITHOUT_APPROVER].append(item["id"])

    if not edges:
        return found
    has_predecessor = {successor for _, successor in edges}
    has_successor = {predecessor for predecessor, _ in edges}
    top = [item for item in items if not item.get("parent_id")]
    starts = [item["start_date"] for item in top if item.get("start_date")]
    finishes = [item["finish_date"] for item in top if item.get("finish_date")]
    first_start = min(starts) if starts else None
    last_finish = max(finishes) if finishes else None
    for item in top:
        if item["id"] not in has_predecessor and not (first_start and item.get("start_date") == first_start):
            found[NO_PREDECESSOR].append(item["id"])
        if (
            item["id"] not in has_successor
            and not item.get("target_date")
            and not (last_finish and item.get("finish_date") == last_finish)
        ):
            found[NO_SUCCESSOR].append(item["id"])
    return found


def department_warnings(departments):
    """
    The departments that tell nobody, from ``[{"group_id", "is_active", "member_count", "project_member_count"}]``,
    with the reason: switched off, no members, or none of them in the project.
    """
    found = []
    for department in departments:
        if not department["is_active"]:
            reason = INACTIVE
        elif department["member_count"] == 0:
            reason = NO_MEMBERS
        elif department["project_member_count"] == 0:
            reason = NO_PROJECT_MEMBERS
        else:
            continue
        found.append({**department, "reason": reason})
    return found


def _open_items(project):
    return (
        Issue.issue_objects.filter(project=project)
        .exclude(state__group__in=[StateGroup.COMPLETED.value, StateGroup.CANCELLED.value])
        .exclude(type__kind="review")
        .order_by("sequence_id")
    )


def project_raci_warnings(project, max_listed=MAX_LISTED):
    """
    The warnings of a project: ``{"counts": {kind: n}, "items": {kind: [work item]}, "departments": [...],
    "max_listed": n}``. A work item is ``{"id", "name", "sequence_id"}``; each list names at most ``max_listed``.
    """
    items = list(
        _open_items(project).values(
            "id", "name", "sequence_id", "parent_id", "start_date", "finish_date", "target_date", "type__kind"
        )
    )
    item_ids = [item["id"] for item in items]
    for item in items:
        item["kind"] = item.pop("type__kind")

    raci_rows = list(
        IssueRaci.objects.filter(
            issue_id__in=item_ids, group__kind=GroupKind.DEPARTMENT, group__deleted_at__isnull=True
        ).values_list("issue_id", "group_id", "role")
    )
    roles = defaultdict(set)
    for issue_id, _, role in raci_rows:
        roles[issue_id].add(role)

    relations = IssueRelation.objects.filter(
        Q(issue__project=project) | Q(related_issue__project=project),
        relation_type__in=STORED_TIMELINE_RELATION_TYPES,
    ).values_list("issue_id", "related_issue_id", "relation_type")
    edges = predecessor_edges(relations)

    found = item_warnings(items, roles, edges)
    by_id = {item["id"]: item for item in items}

    group_ids = {group_id for _, group_id, _ in raci_rows}
    project_members = ProjectMember.objects.filter(project=project, is_active=True).values("member_id")
    member_counts = defaultdict(int)
    project_member_counts = defaultdict(int)
    for group_id, user_id, in_project in _memberships(project, group_ids, project_members):
        member_counts[group_id] += 1
        if in_project:
            project_member_counts[group_id] += 1
    departments = department_warnings(
        [
            {
                "group_id": str(group_id),
                "is_active": is_active,
                "member_count": member_counts[group_id],
                "project_member_count": project_member_counts[group_id],
            }
            for group_id, is_active in UserGroup.objects.filter(pk__in=group_ids)
            .order_by("sort_order", "name")
            .values_list("id", "is_active")
        ]
    )

    def listed(ids):
        return [
            {"id": str(pk), "name": by_id[pk]["name"], "sequence_id": by_id[pk]["sequence_id"]}
            for pk in ids[:max_listed]
        ]

    return {
        "counts": {**{kind: len(ids) for kind, ids in found.items()}, "department_without_members": len(departments)},
        "items": {kind: listed(ids) for kind, ids in found.items()},
        "departments": departments,
        "max_listed": max_listed,
    }


def _memberships(project, group_ids, project_members):
    """``(group id, user id, is the person an active project member)`` for the active departments among these."""
    if not group_ids:
        return []
    in_project = set(
        department_memberships(project.workspace_id)
        .filter(group_id__in=list(group_ids), user_id__in=project_members)
        .values_list("group_id", "user_id")
    )
    return [
        (group_id, user_id, (group_id, user_id) in in_project)
        for group_id, user_id in department_memberships(project.workspace_id)
        .filter(group_id__in=list(group_ids))
        .values_list("group_id", "user_id")
    ]
