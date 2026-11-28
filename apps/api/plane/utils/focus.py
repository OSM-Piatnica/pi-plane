# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Focus: what a person should do next, what holds them up and who waits for them (roadmap step D9).

The lists, for one person in one workspace (or one project of it):

* **next**: my open work items, those I can start first, then by ``start_date`` and ``finish_date``;
* **blocked**: my open work items that a predecessor holds up, with the predecessors and who has them;
* **waiting_on_us**: open work items of other people that one of my work items holds up;
* **to_approve**: open work items on which one of my departments is the approver (RACI);
* **overdue**: my open work items whose due date (``target_date``) or planned finish (``finish_date``) has passed.

"My work items" are those assigned to me, directly or through a group I belong to (a group counts the groups below
it, as for group assignees). "My departments" are every active department group I belong to directly, so the lists
do not depend on one department per person (decision 13, #508). Open means a state outside the completed and
cancelled groups; archived, draft and triage work items never take part.

A predecessor holds a work item up while the date rule between them cannot be met yet:

============================  ===========================  ======================================
relation (seen from the item)  the predecessor has to       what the item cannot do before that
============================  ===========================  ======================================
blocked by                     be completed (or cancelled)  start
starts after                   be started                   start
finishes after                 be completed (or cancelled)  finish
finishes after start           be started                   finish
============================  ===========================  ======================================

An item held up only in its finish can still be started, so "next" counts it as startable. Other relations (relates
to, duplicate, ...) hold nothing up.

Only work items the person may see take part, by the rules of the work item lists: those of projects they are an
active member of, and for a guest of a project that does not show guests everything, only those they created. A
predecessor the person may not see is counted, not shown.

The number of queries does not depend on the number of work items: each list is one query for its items and one for
its count, and the predecessors of the shown items take one more each.
"""

import datetime
import operator
from functools import reduce
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Subquery, UUIDField, Value, When
from django.db.models.functions import Coalesce

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueGroupAssignee,
    IssueRelation,
    ProjectMember,
    RaciRole,
    WorkspaceMember,
)
from plane.utils.raci import department_ids_of, live_raci_rows, workspace_raci_enabled
from plane.utils.user_groups import group_ids_of_user

ADMIN_ROLE = 20
GUEST_ROLE = 5

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

DONE_GROUPS = ("completed", "cancelled")
STARTED_GROUPS = ("started", "completed", "cancelled")

# A stored relation ``issue <type> related_issue``: is the predecessor the issue (else the related issue), does it hold
# up the start (else the finish) of the other one, has the predecessor to be done (else only started), and the name of
# the relation as the held-up work item sees it
HOLDING_RULES = {
    "blocked_by": {"predecessor_is_issue": False, "holds": "start", "needs": "done", "seen_as": "blocked_by"},
    "start_before": {"predecessor_is_issue": True, "holds": "start", "needs": "started", "seen_as": "start_after"},
    "finish_before": {"predecessor_is_issue": True, "holds": "finish", "needs": "done", "seen_as": "finish_after"},
    "start_before_finish": {
        "predecessor_is_issue": True,
        "holds": "finish",
        "needs": "started",
        "seen_as": "finish_after_start",
    },
}

ITEM_FIELDS = (
    "id",
    "name",
    "sequence_id",
    "project_id",
    "state_id",
    "priority",
    "start_date",
    "finish_date",
    "target_date",
)


def clamp_limit(raw):
    """The number of work items per list asked for, within 1 and ``MAX_LIMIT``; ``DEFAULT_LIMIT`` when unreadable."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(MAX_LIMIT, value))


def today_for(user):
    """Today in the person's time zone (UTC when it is not known)."""
    try:
        zone = ZoneInfo(getattr(user, "user_timezone", None) or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return datetime.datetime.now(zone).date()


def overdue_reasons(item, today):
    """Why an open work item is overdue: ``"due"`` when its due date has passed, ``"finish"`` for its planned finish."""
    reasons = []
    if item.get("target_date") is not None and item["target_date"] < today:
        reasons.append("due")
    if item.get("finish_date") is not None and item["finish_date"] < today:
        reasons.append("finish")
    return reasons


def visible_issues_q(user, workspace_id):
    """
    A Q (on Issue) for the work items the person may see in the workspace.

    Projects they are an active member of; where they are a guest and the project does not show guests everything,
    only the work items they created. A workspace admin sees everything of their projects, as in work item detail.
    Two queries.
    """
    is_workspace_admin = WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member=user, role=ADMIN_ROLE, is_active=True
    ).exists()
    everything, own_only = [], []
    rows = ProjectMember.objects.filter(
        workspace_id=workspace_id,
        member=user,
        is_active=True,
        project__deleted_at__isnull=True,
        project__archived_at__isnull=True,
    ).values_list("project_id", "role", "project__guest_view_all_features")
    for project_id, role, guests_see_all in rows:
        if role > GUEST_ROLE or guests_see_all or is_workspace_admin:
            everything.append(project_id)
        else:
            own_only.append(project_id)
    return Q(project_id__in=everything) | Q(project_id__in=own_only, created_by=user)


def mine_q(user, group_ids):
    """A Q (on Issue) for the work items assigned to the person, directly or through one of ``group_ids``."""
    q = Q(pk__in=IssueAssignee.objects.filter(assignee=user, deleted_at__isnull=True).values("issue_id"))
    if group_ids:
        q |= Q(
            pk__in=IssueGroupAssignee.objects.filter(group_id__in=list(group_ids), deleted_at__isnull=True).values(
                "issue_id"
            )
        )
    return q


def _rule_q(relation_type, rule):
    """The relations of one type whose predecessor still holds the other work item up."""
    side = "issue" if rule["predecessor_is_issue"] else "related_issue"
    groups = DONE_GROUPS if rule["needs"] == "done" else STARTED_GROUPS
    return Q(relation_type=relation_type, **{f"{side}__deleted_at__isnull": True}) & ~Q(
        **{f"{side}__state__group__in": groups}
    )


def holding_links():
    """
    The relations whose predecessor still holds the other work item up, annotated with ``predecessor_id``,
    ``successor_id`` and ``holds_start`` (else only the finish is held up).
    """
    rules = reduce(operator.or_, (_rule_q(relation_type, rule) for relation_type, rule in HOLDING_RULES.items()))
    # the types stored with the held-up work item first ("issue blocked_by related_issue")
    successor_first = [t for t, rule in HOLDING_RULES.items() if not rule["predecessor_is_issue"]]
    holds_start = [t for t, rule in HOLDING_RULES.items() if rule["holds"] == "start"]
    return (
        IssueRelation.objects.filter(rules, deleted_at__isnull=True)
        .annotate(
            predecessor_id=Case(
                When(relation_type__in=successor_first, then=F("related_issue_id")),
                default=F("issue_id"),
                output_field=UUIDField(),
            ),
            successor_id=Case(
                When(relation_type__in=successor_first, then=F("issue_id")),
                default=F("related_issue_id"),
                output_field=UUIDField(),
            ),
            holds_start=Case(
                When(relation_type__in=holds_start, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        .order_by()
    )


def _assignee_ids():
    return Coalesce(
        Subquery(
            IssueAssignee.objects.filter(issue_id=OuterRef("pk"), deleted_at__isnull=True)
            .values("issue_id")
            .annotate(ids=ArrayAgg("assignee_id", distinct=True))
            .values("ids")
        ),
        Value([], output_field=ArrayField(UUIDField())),
    )


def _group_assignee_ids():
    return Coalesce(
        Subquery(
            IssueGroupAssignee.objects.filter(issue_id=OuterRef("pk"), deleted_at__isnull=True)
            .values("issue_id")
            .annotate(ids=ArrayAgg("group_id", distinct=True))
            .values("ids")
        ),
        Value([], output_field=ArrayField(UUIDField())),
    )


def _items(queryset, limit, *extra):
    """The first ``limit`` work items of a queryset as plain dicts, with their project, state group and assignees."""
    rows = queryset.annotate(
        project_identifier=F("project__identifier"),
        state_group=F("state__group"),
        assignee_ids=_assignee_ids(),
        group_assignee_ids=_group_assignee_ids(),
    ).values(*ITEM_FIELDS, "project_identifier", "state_group", "assignee_ids", "group_assignee_ids", *extra)[:limit]
    return [dict(row) for row in rows]


def _section(queryset, limit, *extra):
    return {"count": queryset.count(), "items": _items(queryset, limit, *extra)}


def _links_by_successor(successor_ids, predecessor_filter=None):
    """``{successor id: [(predecessor id, relation type)]}`` for the holding relations of the given work items."""
    links = holding_links().filter(successor_id__in=list(successor_ids))
    if predecessor_filter is not None:
        links = links.filter(predecessor_id__in=predecessor_filter)
    found = {}
    for successor_id, predecessor_id, relation_type in links.values_list(
        "successor_id", "predecessor_id", "relation_type"
    ):
        found.setdefault(successor_id, []).append((predecessor_id, relation_type))
    return found


def _attach_predecessors(items, visible_q, key, predecessor_filter=None):
    """
    Give every work item in ``items`` the predecessors that hold it up, under ``key``: the predecessor (shown like
    an item), the relation as the held-up item sees it and what is held up (``"start"`` or ``"finish"``). Predecessors
    the person may not see are only counted (``hidden_<key>_count``). Two queries, whatever the number of items.
    """
    links = _links_by_successor([item["id"] for item in items], predecessor_filter)
    predecessor_ids = {predecessor_id for pairs in links.values() for predecessor_id, _ in pairs}
    shown = {}
    if predecessor_ids:
        shown = {
            row["id"]: row
            for row in _items(Issue.objects.filter(visible_q, pk__in=list(predecessor_ids)), len(predecessor_ids))
        }
    for item in items:
        entries, hidden = [], 0
        for predecessor_id, relation_type in links.get(item["id"], []):
            predecessor = shown.get(predecessor_id)
            if predecessor is None:
                hidden += 1
                continue
            rule = HOLDING_RULES[relation_type]
            entries.append({"relation_type": rule["seen_as"], "holds": rule["holds"], "issue": predecessor})
        entries.sort(
            key=lambda entry: (
                entry["holds"] != "start",
                entry["issue"]["project_identifier"] or "",
                entry["issue"]["sequence_id"] or 0,
            )
        )
        item[key] = entries
        item[f"hidden_{key}_count"] = hidden
    return items


def focus(user, workspace, project_id=None, limit=DEFAULT_LIMIT):
    """
    The focus lists of a person in a workspace, or only in one project of it. Each list is
    ``{"count": <all that match>, "items": [<the first `limit`>]}``.
    """
    today = today_for(user)
    visible = visible_issues_q(user, workspace.id)
    group_ids = group_ids_of_user(workspace.id, user.id)
    mine = mine_q(user, group_ids)

    scope = Issue.issue_objects.filter(visible, workspace_id=workspace.id).exclude(state__group__in=DONE_GROUPS)
    if project_id is not None:
        scope = scope.filter(project_id=project_id)
    my_open = scope.filter(mine)

    held = holding_links().filter(successor_id=OuterRef("pk"))
    held_start = held.filter(holds_start=True)
    nulls_last = {"nulls_last": True}

    next_items = my_open.annotate(startable=~Exists(held_start)).order_by(
        F("startable").desc(),
        F("start_date").asc(**nulls_last),
        F("finish_date").asc(**nulls_last),
        "sequence_id",
    )
    blocked_items = my_open.filter(Exists(held)).order_by(
        F("start_date").asc(**nulls_last), F("finish_date").asc(**nulls_last), "sequence_id"
    )

    # my predecessors may sit in another project than the work items they hold up
    my_open_anywhere = Issue.issue_objects.filter(visible, mine, workspace_id=workspace.id).exclude(
        state__group__in=DONE_GROUPS
    )
    waiting_items = (
        scope.exclude(mine)
        .filter(Exists(held.filter(predecessor_id__in=my_open_anywhere.values("pk"))))
        .order_by(F("start_date").asc(**nulls_last), F("finish_date").asc(**nulls_last), "sequence_id")
    )

    overdue_items = my_open.filter(Q(target_date__lt=today) | Q(finish_date__lt=today)).order_by(
        F("target_date").asc(**nulls_last), F("finish_date").asc(**nulls_last), "sequence_id"
    )

    result = {
        "today": today,
        "next": _section(next_items, limit, "startable"),
        "blocked": _section(blocked_items, limit),
        "waiting_on_us": _section(waiting_items, limit),
        "overdue": _section(overdue_items, limit),
    }
    _attach_predecessors(result["blocked"]["items"], visible, "blocked_by")
    _attach_predecessors(result["waiting_on_us"]["items"], visible, "waiting_on", my_open_anywhere.values("pk"))
    for item in result["overdue"]["items"]:
        item["overdue"] = overdue_reasons(item, today)

    result.update(_to_approve(user, workspace, scope, limit))
    return result


def _to_approve(user, workspace, scope, limit):
    """
    Open work items on which one of my departments is the approver, with ``approver_department_ids`` (mine only).

    Approval steps (workstream C) are not part of it yet. Empty, with ``department_ids`` empty, for a person without
    a department; empty too while RACI is off for the workspace (``raci_enabled``).
    """
    department_ids = department_ids_of(user, workspace.id)
    raci_enabled = workspace_raci_enabled(workspace)
    answer = {"department_ids": sorted(str(group_id) for group_id in department_ids), "raci_enabled": raci_enabled}
    if not department_ids or not raci_enabled:
        answer["to_approve"] = {"count": 0, "items": []}
        return answer

    rows = live_raci_rows().filter(workspace_id=workspace.id, group_id__in=list(department_ids), role=RaciRole.APPROVER)
    items = scope.filter(pk__in=rows.values("issue_id")).order_by(
        F("target_date").asc(nulls_last=True), F("finish_date").asc(nulls_last=True), "sequence_id"
    )
    section = _section(items, limit)
    approvers = {}
    for issue_id, group_id in rows.filter(issue_id__in=[item["id"] for item in section["items"]]).values_list(
        "issue_id", "group_id"
    ):
        approvers.setdefault(issue_id, []).append(str(group_id))
    for item in section["items"]:
        item["approver_department_ids"] = sorted(approvers.get(item["id"], []))
    answer["to_approve"] = section
    return answer
