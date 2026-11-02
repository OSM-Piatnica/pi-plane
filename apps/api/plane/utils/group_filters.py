# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Filtering work items, modules, cycles and projects by user group.

A filter value is a list of tokens: a group id, ``my_groups`` or ``none``. Who may filter by which group is
decided here, on the server: a workspace admin may use any group of the workspace, everybody else only the
groups they belong to (their own and the ones above them). A group id outside that set is dropped, and a
filter that asked for groups but is left with nothing to match finds nothing instead of everything.
"""

import uuid
from dataclasses import dataclass, field

from django.db.models import Q

from plane.db.models import (
    IssueGroupAssignee,
    Module,
    ModuleMember,
    ProjectGroup,
    UserGroup,
    UserGroupMember,
    Workspace,
)
from plane.utils.user_groups import _parent_map, ancestor_ids, descendant_ids, group_ids_of_user, is_workspace_admin

MY_GROUPS = "my_groups"
NO_GROUP = "none"


def split_group_tokens(values):
    """Split a filter value (list or comma separated text) into (group ids, my_groups, none). Rubbish is ignored."""
    if values is None:
        return set(), False, False
    if isinstance(values, str):
        values = values.split(",")
    ids = set()
    my_groups = False
    none = False
    for raw in values:
        token = str(raw).strip()
        if not token or token == "null":
            continue
        if token == MY_GROUPS:
            my_groups = True
        elif token.lower() == NO_GROUP:
            none = True
        else:
            try:
                ids.add(uuid.UUID(token))
            except ValueError:
                continue
    return ids, my_groups, none


@dataclass
class GroupFilter:
    """A group filter after the server has applied what the requester may use."""

    workspace_id: object = None
    group_ids: set = field(default_factory=set)  # allowed ids that were asked for
    my_groups: bool = False
    none: bool = False
    mine: set = field(default_factory=set)  # every group the requester belongs to
    allowed: set = field(default_factory=set)  # every group the requester may filter by
    requested_ids: bool = False

    @property
    def active(self):
        return bool(self.group_ids or self.my_groups or self.none or self.requested_ids)

    @property
    def empty(self):
        """Groups were asked for, none may be used and no keyword is left: nothing can match."""
        return self.requested_ids and not self.group_ids and not self.my_groups and not self.none


def allowed_group_ids(user, workspace_id):
    """(groups the requester may filter by, every group they belong to). Admins may use every group."""
    mine = group_ids_of_user(workspace_id, user.id) if user is not None and user.id else set()
    if user is not None and user.id and is_workspace_admin(user, workspace_id):
        return set(UserGroup.objects.filter(workspace_id=workspace_id).values_list("id", flat=True)), mine
    return set(mine), mine


def resolve_group_filter(user, workspace_id, values):
    """Apply the rules of who may filter by what to a requested filter value."""
    ids, my_groups, none = split_group_tokens(values)
    resolved = GroupFilter(workspace_id=workspace_id, my_groups=my_groups, none=none, requested_ids=bool(ids))
    if workspace_id is None:
        return resolved
    if ids or my_groups:
        resolved.allowed, resolved.mine = allowed_group_ids(user, workspace_id)
        resolved.group_ids = ids & resolved.allowed
    return resolved


def workspace_id_from_slug(slug):
    if not slug:
        return None
    return Workspace.objects.filter(slug=slug).values_list("id", flat=True).first()


def resolve_for_request(request, values, slug=None):
    """``resolve_group_filter`` for the person and workspace of a request (workspace taken from the URL)."""
    if request is None:
        return resolve_group_filter(None, None, values)
    if slug is None:
        context = getattr(request, "parser_context", None) or {}
        slug = (context.get("kwargs") or {}).get("slug")
    return resolve_group_filter(getattr(request, "user", None), workspace_id_from_slug(slug), values)


def issue_group_q(resolved):
    """A Q matching work items (use it on a queryset of Issue) for a resolved group filter."""
    if resolved.empty:
        return Q(pk__in=[])
    assigned = IssueGroupAssignee.objects.filter(deleted_at__isnull=True)
    parts = []
    if resolved.group_ids:
        below = descendant_ids(resolved.workspace_id, resolved.group_ids)
        parts.append(Q(pk__in=assigned.filter(group_id__in=below).values("issue_id")))
    if resolved.my_groups and resolved.mine:
        parts.append(Q(pk__in=assigned.filter(group_id__in=resolved.mine).values("issue_id")))
    if resolved.none:
        parts.append(~Q(pk__in=assigned.values("issue_id")))
    if not parts:
        return Q(pk__in=[])
    combined = parts[0]
    for part in parts[1:]:
        combined |= part
    return combined


def _direct_groups_of_users(workspace_id, user_ids):
    groups = {}
    rows = UserGroupMember.objects.filter(workspace_id=workspace_id, user_id__in=user_ids).values_list(
        "user_id", "group_id"
    )
    for user_id, group_id in rows:
        groups.setdefault(user_id, set()).add(group_id)
    return groups


def _with_ancestors(workspace_id, groups, parents):
    result = set(groups)
    for group_id in groups:
        result.update(ancestor_ids(workspace_id, group_id, parents))
    return result


def groups_of_modules(workspace_id, module_ids):
    """module id -> the groups of its lead and members (direct groups only)."""
    people = {}
    for module_id, lead_id in Module.objects.filter(id__in=module_ids).values_list("id", "lead_id"):
        if lead_id:
            people.setdefault(module_id, set()).add(lead_id)
    for module_id, member_id in ModuleMember.objects.filter(
        module_id__in=module_ids, deleted_at__isnull=True
    ).values_list("module_id", "member_id"):
        people.setdefault(module_id, set()).add(member_id)
    everyone = set().union(*people.values()) if people else set()
    by_user = _direct_groups_of_users(workspace_id, everyone) if everyone else {}
    return {
        module_id: set().union(*(by_user.get(user_id, set()) for user_id in users)) if users else set()
        for module_id, users in people.items()
    }


def groups_of_cycles(workspace_id, cycle_ids):
    """cycle id -> the groups its work items are assigned to (direct groups only)."""
    groups = {}
    rows = IssueGroupAssignee.objects.filter(
        deleted_at__isnull=True,
        issue__deleted_at__isnull=True,
        issue__archived_at__isnull=True,
        issue__is_draft=False,
        issue__issue_cycle__cycle_id__in=cycle_ids,
        issue__issue_cycle__deleted_at__isnull=True,
    ).values_list("issue__issue_cycle__cycle_id", "group_id")
    for cycle_id, group_id in rows:
        groups.setdefault(cycle_id, set()).add(group_id)
    return groups


def groups_of_projects(workspace_id, project_ids):
    """project id -> the groups that are project groups of it (direct links only)."""
    groups = {}
    rows = ProjectGroup.objects.filter(
        workspace_id=workspace_id,
        project_id__in=project_ids,
        deleted_at__isnull=True,
        group__deleted_at__isnull=True,
    ).values_list("project_id", "group_id")
    for project_id, group_id in rows:
        groups.setdefault(project_id, set()).add(group_id)
    return groups


def groups_of_issues(workspace_id, issue_ids):
    """work item id -> the groups it is assigned to (direct groups only)."""
    groups = {}
    rows = IssueGroupAssignee.objects.filter(deleted_at__isnull=True, issue_id__in=issue_ids).values_list(
        "issue_id", "group_id"
    )
    for issue_id, group_id in rows:
        groups.setdefault(issue_id, set()).add(group_id)
    return groups


def group_info(request, slug, kind, ids):
    """
    For modules (``kind="module"``), cycles (``"cycle"``), projects (``"project"``) or work items (``"issue"``):
    id -> the facts the group filter works on.

    ``group_ids``: the groups the item is in (with the groups above them) that the requester may filter by;
    ``has_group``: it is in any group at all; ``in_my_groups``: it matches ``my_groups``.
    """
    ids = [item if isinstance(item, uuid.UUID) else uuid.UUID(str(item)) for item in ids]
    workspace_id = workspace_id_from_slug(slug)
    if workspace_id is None or not ids:
        return {}
    user = request.user
    allowed, mine = allowed_group_ids(user, workspace_id)
    if kind == "module":
        direct = groups_of_modules(workspace_id, ids)
    elif kind == "project":
        direct = groups_of_projects(workspace_id, ids)
    elif kind == "issue":
        direct = groups_of_issues(workspace_id, ids)
    else:
        direct = groups_of_cycles(workspace_id, ids)
    parents = _parent_map(workspace_id)
    info = {}
    for item_id in ids:
        own = direct.get(item_id, set())
        if kind == "project":
            # A project group stands for the groups below it too, so a subgroup finds the project of its parent group
            expanded = descendant_ids(workspace_id, own, parents) if own else set()
        else:
            expanded = _with_ancestors(workspace_id, own, parents)
        # A module is "in" a group a person of it belongs to, so my groups are tested against the expanded set;
        # a cycle, a project or a work item matches my groups through the groups it holds itself.
        mine_hit = bool((expanded if kind == "module" else own) & mine)
        info[str(item_id)] = {
            "group_ids": sorted(str(group_id) for group_id in expanded & allowed),
            "has_group": bool(own),
            "in_my_groups": mine_hit,
        }
    return info


def filter_by_groups_param(request, slug, kind, queryset, param="groups"):
    """Narrow a queryset of modules or cycles by the ``groups`` query parameter (no parameter, no change)."""
    raw = request.query_params.get(param)
    if raw is None or not str(raw).strip():
        return queryset
    workspace_id = workspace_id_from_slug(slug)
    resolved = resolve_group_filter(request.user, workspace_id, raw)
    if not resolved.active:
        return queryset
    if resolved.empty:
        return queryset.none()
    ids = list(dict.fromkeys(queryset.values_list("id", flat=True)))
    info = group_info(request, slug, kind, ids)
    wanted = {str(group_id) for group_id in resolved.group_ids}
    keep = []
    for item_id in ids:
        facts = info.get(str(item_id))
        if facts is None:
            continue
        if (
            (wanted and wanted & set(facts["group_ids"]))
            or (resolved.my_groups and facts["in_my_groups"])
            or (resolved.none and not facts["has_group"])
        ):
            keep.append(item_id)
    return queryset.filter(id__in=keep)


def add_group_info(request, slug, kind, rows):
    """Add ``group_ids`` / ``has_group`` / ``in_my_groups`` to every row (a dict with an ``id``) of a list response."""
    rows = list(rows)
    info = group_info(request, slug, kind, [row["id"] for row in rows])
    for row in rows:
        row.update(info.get(str(row["id"]), {"group_ids": [], "has_group": False, "in_my_groups": False}))
    return rows
