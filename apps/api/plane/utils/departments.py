# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Departments: user groups of kind "department", and the one department a person has in a workspace.

A department is a user group, so it nests, takes members, can be mirrored from the identity provider and can be
assigned work like any other group. On top of that a workspace member has at most one department
(``WorkspaceMember.department``). The two are kept in step here:

* a person's department is always a group they belong to: choosing a local department puts them in it, and taking
  them out of the group (by hand, or by the sign-in sync) clears the department;
* changing the department takes the person out of the previous one, unless the identity provider put them there;
* a department managed by the identity provider can only be chosen by people the provider put in it;
* a person may belong to further department groups by hand; only the one on the workspace member is "theirs".
"""

import re

from django.db import transaction
from django.db.models import Max

from plane.db.models import GroupKind, GroupRole, UserGroup, UserGroupMember, WorkspaceMember
from plane.utils.project_groups import reconcile_user

COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
SORT_ORDER_STEP = 10000


class DepartmentError(ValueError):
    """A department that cannot be given to a person; the message is shown to whoever asked."""


def normalize_code(value):
    """Codes are short labels ("RM"): compared and stored in upper case, without the spaces around them."""
    return (value or "").strip().upper()


def is_valid_color(value):
    return value == "" or bool(COLOR_PATTERN.match(value))


def next_sort_order(workspace_id):
    """The place after the last department of the workspace."""
    largest = UserGroup.objects.filter(workspace_id=workspace_id, kind=GroupKind.DEPARTMENT).aggregate(
        largest=Max("sort_order")
    )["largest"]
    return SORT_ORDER_STEP if largest is None else largest + SORT_ORDER_STEP


def code_taken(workspace_id, code, exclude_id=None):
    """True when another department of the workspace already has this code."""
    if not code:
        return False
    taken = UserGroup.objects.filter(workspace_id=workspace_id, kind=GroupKind.DEPARTMENT, code=code)
    if exclude_id:
        taken = taken.exclude(pk=exclude_id)
    return taken.exists()


def active_departments(workspace_id):
    """The departments a person can choose from, in their order."""
    return UserGroup.objects.filter(workspace_id=workspace_id, kind=GroupKind.DEPARTMENT, is_active=True).order_by(
        "sort_order", "name"
    )


def set_department(workspace_member, department):
    """
    Give a workspace member a department (a UserGroup), or none (``None``), keeping the group memberships in step.

    Raises DepartmentError when the group cannot be the person's department.
    """
    previous_id = workspace_member.department_id
    new_id = department.id if department is not None else None
    if previous_id == new_id:
        return workspace_member
    user_id = workspace_member.member_id
    workspace_id = workspace_member.workspace_id

    is_member = False
    if department is not None:
        if department.workspace_id != workspace_id:
            raise DepartmentError("The department does not exist in this workspace.")
        if department.kind != GroupKind.DEPARTMENT:
            raise DepartmentError("This group is not a department.")
        if not department.is_active:
            raise DepartmentError("This department is switched off and cannot be chosen.")
        is_member = UserGroupMember.objects.filter(group=department, user_id=user_id).exists()
        if department.is_external and not is_member:
            raise DepartmentError(
                "This department is managed by the identity provider, which decides who belongs to it."
            )

    with transaction.atomic():
        if previous_id:
            # Only what was put in by hand is taken out: the provider's memberships are its own
            UserGroupMember.objects.filter(group_id=previous_id, user_id=user_id, managed_externally=False).delete()
        if department is not None and not is_member:
            UserGroupMember.objects.create(
                workspace_id=workspace_id, group=department, user_id=user_id, role=GroupRole.MEMBER
            )
        workspace_member.department = department
        workspace_member.save(update_fields=["department", "updated_at"])
    reconcile_user(workspace_id, user_id)
    return workspace_member


def adopt_department(workspace_id, user_id, group):
    """A person without a department who is put in a department group gets it as their department."""
    if group.kind != GroupKind.DEPARTMENT or not group.is_active:
        return
    WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member_id=user_id, is_active=True, department__isnull=True
    ).update(department=group)


def clear_department(workspace_id, group_ids, user_id=None):
    """Nobody keeps a department they no longer belong to, or a group that stopped being a department."""
    members = WorkspaceMember.objects.filter(workspace_id=workspace_id, department_id__in=list(group_ids))
    if user_id is not None:
        members = members.filter(member_id=user_id)
    members.update(department=None)
