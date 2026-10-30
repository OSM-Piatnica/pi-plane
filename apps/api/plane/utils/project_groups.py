# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Groups as members of a project.

A project may have user groups as members, next to people. Whoever belongs to a group (counting the groups below it)
is a member of the project with the role given to the group. ``ProjectMember.role`` and ``is_active`` always hold the
effective values, so no permission check needs to know about groups; this module keeps them right:

* a person's own (direct) role always counts, a group can only raise it: role = max(direct role, best group role);
* the role a group gives is capped by the person's workspace role (a workspace guest stays a guest);
* only active members of the workspace get a project through a group.

Columns of ``ProjectMember`` that carry the bookkeeping:

* ``via_group``: the person belongs to the project only through groups;
* ``group_role``: the best role the groups give them (None when none does);
* ``direct_role``: the person's own role, kept only while a group raised the effective role above it.
"""

from django.db.models import Min, Q
from rest_framework.exceptions import APIException
from django.utils import timezone

from plane.db.models import (
    ProjectGroup,
    ProjectMember,
    ProjectUserProperty,
    UserGroupMember,
    WorkspaceMember,
)
from plane.utils.user_groups import _parent_map, ancestor_ids, descendant_ids, member_user_ids

BATCH = 500
FROM_GROUP_ONLY_MESSAGE = (
    "This person belongs to the project through a group. Remove the group, or the person from the group."
)
ASSIGNABLE_GROUP_MESSAGE = "A work item can only be assigned to groups that are members of its project."


class GroupNotInProjectError(APIException):
    """A work item was assigned to a group that is not a member of its project (answers 400 {"error": ...})."""

    status_code = 400
    default_detail = {"error": ASSIGNABLE_GROUP_MESSAGE}
    default_code = "group_not_in_project"


class MemberThroughGroupError(Exception):
    """A person who is in a project only through groups cannot be removed from it by hand."""


def _group_roles_by_project(workspace_id, project_ids=None):
    """{project_id: {group_id: role}} of the live links of a workspace."""
    links = ProjectGroup.objects.filter(
        workspace_id=workspace_id, group__deleted_at__isnull=True, project__deleted_at__isnull=True
    )
    if project_ids is not None:
        links = links.filter(project_id__in=project_ids)
    result = {}
    for project_id, group_id, role in links.values_list("project_id", "group_id", "role"):
        result.setdefault(project_id, {})[group_id] = role
    return result


def _groups_of_users(workspace_id, user_ids, parents):
    """{user_id: every group they belong to}: their own and the groups above them."""
    direct = {}
    for user_id, group_id in UserGroupMember.objects.filter(
        workspace_id=workspace_id, user_id__in=user_ids
    ).values_list("user_id", "group_id"):
        direct.setdefault(user_id, set()).add(group_id)
    result = {}
    cache = {}
    for user_id, groups in direct.items():
        full = set(groups)
        for group_id in groups:
            if group_id not in cache:
                cache[group_id] = ancestor_ids(workspace_id, group_id, parents)
            full.update(cache[group_id])
        result[user_id] = full
    return result


def _reconcile(workspace_id, user_ids, project_ids=None):
    """Bring the project memberships of ``user_ids`` in line with the groups (in ``project_ids`` only, if given)."""
    user_ids = list(user_ids)
    if not user_ids:
        return
    for start in range(0, len(user_ids), BATCH):
        _reconcile_batch(workspace_id, user_ids[start : start + BATCH], project_ids)


def _reconcile_batch(workspace_id, user_ids, project_ids):
    links = _group_roles_by_project(workspace_id, project_ids)
    parents = _parent_map(workspace_id)
    user_groups = _groups_of_users(workspace_id, user_ids, parents) if links else {}
    workspace_roles = dict(
        WorkspaceMember.objects.filter(workspace_id=workspace_id, member_id__in=user_ids, is_active=True).values_list(
            "member_id", "role"
        )
    )

    # What the groups give: {(user, project): role}
    desired = {}
    for project_id, roles in links.items():
        for user_id, groups in user_groups.items():
            workspace_role = workspace_roles.get(user_id)
            if workspace_role is None:
                continue
            best = max((role for group_id, role in roles.items() if group_id in groups), default=None)
            if best is not None:
                desired[(user_id, project_id)] = min(best, workspace_role)

    rows = ProjectMember.objects.filter(workspace_id=workspace_id, member_id__in=user_ids).filter(
        Q(project_id__in={project_id for _, project_id in desired}) | Q(via_group=True) | Q(group_role__isnull=False)
    )
    if project_ids is not None:
        rows = rows.filter(project_id__in=project_ids)
    row_map = {(row.member_id, row.project_id): row for row in rows.select_related("project")}

    now = timezone.now()
    to_update = {}
    to_create = []
    reactivated = []
    for key in set(desired) | set(row_map):
        row = row_map.get(key)
        group_role = desired.get(key)
        if group_role is None:
            if row is not None and _release(row):
                row.updated_at = now
                to_update[row.pk] = row
        elif row is None:
            to_create.append(key + (group_role,))
        elif _grant(row, group_role):
            row.updated_at = now
            to_update[row.pk] = row
            if row.via_group and row.is_active:
                reactivated.append(row)

    if to_update:
        ProjectMember.objects.bulk_update(
            list(to_update.values()),
            ["role", "is_active", "via_group", "group_role", "direct_role", "updated_at"],
            batch_size=100,
        )
    _create_members(workspace_id, to_create)
    _ensure_properties(workspace_id, [(row.member_id, row.project_id) for row in reactivated])


def _release(row):
    """The groups give this person nothing in the project. True when the row changed."""
    if row.via_group:
        row.is_active = False
        row.via_group = False
        row.group_role = None
        row.direct_role = None
        return True
    if row.group_role is not None:
        if row.direct_role is not None:
            row.role = row.direct_role
        row.group_role = None
        row.direct_role = None
        return True
    return False


def _grant(row, group_role):
    """The groups give this person ``group_role`` in the project. True when the row changed."""
    before = (row.role, row.is_active, row.via_group, row.group_role, row.direct_role)
    if not row.is_active:
        # Removed by hand earlier: treated as new
        row.is_active = True
        row.via_group = True
        row.role = group_role
        row.direct_role = None
    elif row.via_group:
        row.role = group_role
        row.direct_role = None
    else:
        direct = row.direct_role if row.group_role is not None and row.direct_role is not None else row.role
        row.role = max(direct, group_role)
        row.direct_role = direct if row.role > direct else None
    row.group_role = group_role
    return before != (row.role, row.is_active, row.via_group, row.group_role, row.direct_role)


def _next_sort_orders(workspace_id, user_ids):
    return {
        item["user_id"]: item["lowest"]
        for item in ProjectUserProperty.objects.filter(workspace_id=workspace_id, user_id__in=user_ids)
        .values("user_id")
        .annotate(lowest=Min("sort_order"))
    }


def _create_members(workspace_id, to_create):
    """Add the people the groups newly bring into projects, with the same side rows other creations make."""
    if not to_create:
        return
    lowest = _next_sort_orders(workspace_id, {user_id for user_id, _, _ in to_create})
    members = []
    properties = []
    for user_id, project_id, role in to_create:
        members.append(
            ProjectMember(
                workspace_id=workspace_id,
                project_id=project_id,
                member_id=user_id,
                role=role,
                group_role=role,
                via_group=True,
                is_active=True,
            )
        )
        floor = lowest.get(user_id)
        sort_order = floor - 10000 if floor is not None else 65535
        lowest[user_id] = sort_order
        properties.append(
            ProjectUserProperty(
                workspace_id=workspace_id, project_id=project_id, user_id=user_id, sort_order=sort_order
            )
        )
    ProjectMember.objects.bulk_create(members, batch_size=100, ignore_conflicts=True)
    ProjectUserProperty.objects.bulk_create(properties, batch_size=100, ignore_conflicts=True)


def _ensure_properties(workspace_id, pairs):
    """A person brought back into a project keeps (or gets again) their sidebar ordering of it."""
    if not pairs:
        return
    existing = set(
        ProjectUserProperty.objects.filter(
            workspace_id=workspace_id, user_id__in={u for u, _ in pairs}, project_id__in={p for _, p in pairs}
        ).values_list("user_id", "project_id")
    )
    missing = [(u, p) for u, p in pairs if (u, p) not in existing]
    if not missing:
        return
    lowest = _next_sort_orders(workspace_id, {u for u, _ in missing})
    properties = []
    for user_id, project_id in missing:
        floor = lowest.get(user_id)
        sort_order = floor - 10000 if floor is not None else 65535
        lowest[user_id] = sort_order
        properties.append(
            ProjectUserProperty(
                workspace_id=workspace_id, project_id=project_id, user_id=user_id, sort_order=sort_order
            )
        )
    ProjectUserProperty.objects.bulk_create(properties, batch_size=100, ignore_conflicts=True)


def _flagged_user_ids(workspace_id, project_id=None):
    rows = ProjectMember.objects.filter(workspace_id=workspace_id).filter(
        Q(via_group=True) | Q(group_role__isnull=False)
    )
    if project_id is not None:
        rows = rows.filter(project_id=project_id)
    return set(rows.values_list("member_id", flat=True))


def reconcile_user(workspace_id, user_id):
    """Work out again what groups give one person in every project of the workspace."""
    _reconcile(workspace_id, [user_id])


def reconcile_member(workspace_id, project_id, user_id):
    """Work out again what groups give one person in one project."""
    _reconcile(workspace_id, [user_id], [project_id])


def reconcile_project(project_id):
    """Work out again who belongs to a project through its groups."""
    from plane.db.models import Project

    workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    if workspace_id is None:
        return
    group_ids = list(
        ProjectGroup.objects.filter(project_id=project_id, group__deleted_at__isnull=True).values_list(
            "group_id", flat=True
        )
    )
    users = member_user_ids(workspace_id, group_ids) if group_ids else set()
    users |= _flagged_user_ids(workspace_id, project_id)
    _reconcile(workspace_id, users, [project_id])


def reconcile_workspace(workspace_id):
    """Work out again everybody's group memberships of projects (after a group was deleted or moved)."""
    users = set(UserGroupMember.objects.filter(workspace_id=workspace_id).values_list("user_id", flat=True))
    users |= _flagged_user_ids(workspace_id)
    _reconcile(workspace_id, users)


def set_direct_role(row, role):
    """A person's own role in the project was set by hand: it counts as direct from now on, groups can only raise it."""
    if not (row.via_group or row.group_role is not None):
        return
    row.via_group = False
    row.direct_role = role
    row.role = role
    row.is_active = True
    row.save(update_fields=["via_group", "direct_role", "role", "is_active", "updated_at"])
    reconcile_member(row.workspace_id, row.project_id, row.member_id)
    row.refresh_from_db()


def remove_member(row):
    """Take a person out of a project by hand. Whoever belongs through a group stays through it."""
    if row.via_group:
        raise MemberThroughGroupError(FROM_GROUP_ONLY_MESSAGE)
    if row.group_role is not None:
        row.via_group = True
        row.role = row.group_role
        row.direct_role = None
        row.save(update_fields=["via_group", "role", "direct_role", "updated_at"])
        return
    row.is_active = False
    row.save()


def assignable_group_ids(project_id, workspace_id=None):
    """The groups work items of a project may be assigned to: its groups and every group below them."""
    from plane.db.models import Project

    if workspace_id is None:
        workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    linked = list(
        ProjectGroup.objects.filter(project_id=project_id, group__deleted_at__isnull=True).values_list(
            "group_id", flat=True
        )
    )
    if not linked:
        return set()
    return descendant_ids(workspace_id, linked)


__all__ = [
    "ASSIGNABLE_GROUP_MESSAGE",
    "FROM_GROUP_ONLY_MESSAGE",
    "GroupNotInProjectError",
    "MemberThroughGroupError",
    "assignable_group_ids",
    "reconcile_member",
    "reconcile_project",
    "reconcile_user",
    "reconcile_workspace",
    "remove_member",
    "set_direct_role",
]
