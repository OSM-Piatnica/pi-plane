# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The rules of user groups in one place: nesting, who counts as a member, and who may manage what.

Groups nest (a group has at most one parent) and a person may belong to any number of groups. Belonging
to a group also means belonging to every group above it, so the members of a group are its own members
plus those of all groups below it. A group admin rules over the group and everything below it.
"""

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import OuterRef, Subquery, UUIDField, Value
from django.db.models.functions import Coalesce

from plane.db.models import GroupRole, IssueGroupAssignee, UserGroup, UserGroupMember, WorkspaceMember

# Nesting this deep is far beyond what an organisation chart needs; it only guards against runaway trees.
MAX_GROUP_DEPTH = 10


def _parent_map(workspace_id):
    return dict(UserGroup.objects.filter(workspace_id=workspace_id).values_list("id", "parent_id"))


def descendant_ids(workspace_id, group_ids, parents=None):
    """The given groups and every group below them."""
    parents = parents if parents is not None else _parent_map(workspace_id)
    children = {}
    for child, parent in parents.items():
        children.setdefault(parent, []).append(child)
    found = set()
    pending = list(group_ids)
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(children.get(current, []))
    return found


def ancestor_ids(workspace_id, group_id, parents=None):
    """The groups above a group, nearest first (the group itself is not included)."""
    parents = parents if parents is not None else _parent_map(workspace_id)
    chain = []
    seen = {group_id}
    current = parents.get(group_id)
    while current is not None and current not in seen:
        chain.append(current)
        seen.add(current)
        current = parents.get(current)
    return chain


def depth_of(workspace_id, group_id, parents=None):
    """1 for a top-level group."""
    return len(ancestor_ids(workspace_id, group_id, parents)) + 1


def subtree_height(workspace_id, group_id, parents=None):
    """How many levels the group and everything below it span (1 for a group without subgroups)."""
    parents = parents if parents is not None else _parent_map(workspace_id)
    children = {}
    for child, parent in parents.items():
        children.setdefault(parent, []).append(child)

    def height(node, seen):
        below = [child for child in children.get(node, []) if child not in seen]
        return 1 + max((height(child, seen | {child}) for child in below), default=0)

    return height(group_id, {group_id})


def would_create_cycle(workspace_id, group_id, new_parent_id):
    """True when making ``new_parent_id`` the parent of ``group_id`` would put a group under itself."""
    if new_parent_id is None:
        return False
    return new_parent_id in descendant_ids(workspace_id, [group_id])


def member_user_ids(workspace_id, group_ids):
    """Everyone who belongs to the given groups, counting the groups below them."""
    groups = descendant_ids(workspace_id, group_ids)
    return set(
        UserGroupMember.objects.filter(workspace_id=workspace_id, group_id__in=groups).values_list("user_id", flat=True)
    )


def group_ids_of_user(workspace_id, user_id):
    """Every group a person belongs to: their own, plus the groups above them."""
    parents = _parent_map(workspace_id)
    direct = set(
        UserGroupMember.objects.filter(workspace_id=workspace_id, user_id=user_id).values_list("group_id", flat=True)
    )
    result = set(direct)
    for group_id in direct:
        result.update(ancestor_ids(workspace_id, group_id, parents))
    return result


def is_workspace_admin(user, workspace_id):
    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member=user, role=20, is_active=True, deleted_at__isnull=True
    ).exists()


def administered_group_ids(user, workspace_id):
    """The groups a person rules over: those they administer and everything below them."""
    own = UserGroupMember.objects.filter(
        workspace_id=workspace_id, user=user, role=GroupRole.ADMIN, managed_externally=False
    ).values_list("group_id", flat=True)
    return descendant_ids(workspace_id, list(own))


def can_manage_group(user, workspace_id, group_id, *, admin_checked=None):
    """May the person change this group's members, name and subgroups."""
    admin = is_workspace_admin(user, workspace_id) if admin_checked is None else admin_checked
    return admin or group_id in administered_group_ids(user, workspace_id)


def can_create_group(user, workspace_id, parent_id):
    """A top-level group needs a workspace admin; a subgroup needs rule over its parent."""
    if is_workspace_admin(user, workspace_id):
        return True
    return parent_id is not None and parent_id in administered_group_ids(user, workspace_id)


def can_delete_group(user, workspace_id, group):
    """Whoever rules over the parent may remove a group; a group admin cannot remove the group they administer."""
    if is_workspace_admin(user, workspace_id):
        return True
    return group.parent_id is not None and group.parent_id in administered_group_ids(user, workspace_id)


def group_assignee_ids_annotation():
    """The ids of the groups a work item is assigned to, to annotate a queryset of work items with."""
    return Coalesce(
        Subquery(
            IssueGroupAssignee.objects.filter(issue_id=OuterRef("pk"), deleted_at__isnull=True)
            .values("issue_id")
            .annotate(arr=ArrayAgg("group_id", distinct=True))
            .values("arr")
        ),
        Value([], output_field=ArrayField(UUIDField())),
    )


def issue_ids_assigned_through_groups(user, workspace_id, issue_ids):
    """Of ``issue_ids``, those assigned to a group the person belongs to (a group counts the groups below it)."""
    groups = group_ids_of_user(workspace_id, user.id)
    if not groups:
        return set()
    return set(
        IssueGroupAssignee.objects.filter(issue_id__in=issue_ids, group_id__in=groups).values_list(
            "issue_id", flat=True
        )
    )
