# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Departments: user groups of kind "department".

A department is a user group, so it nests, takes members, can be mirrored from the identity provider, can be a
member of projects and can be assigned work like any other group. There is no separate field on the workspace
member: a person's department is the active department group they belong to. Two rules come on top of a group:

* a person belongs to at most one active department of a workspace; every path that puts someone in a department
  group (adding a member, turning a group into a department, switching a department on, the sign-in sync) keeps it;
* only workspace admins (or the identity provider) manage departments and who is in them, because a department's
  group can make its members members of projects.
"""

import re

from django.db.models import Max

from plane.db.models import GroupKind, UserGroup, UserGroupMember

COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
SORT_ORDER_STEP = 10000
# The longest code the database stores (``UserGroup.code``)
CODE_MAX_LENGTH = 16


class DepartmentError(ValueError):
    """A change that would break the rules of departments; the message is shown to whoever asked."""


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
    """The departments that are switched on, in their order."""
    return UserGroup.objects.filter(workspace_id=workspace_id, kind=GroupKind.DEPARTMENT, is_active=True).order_by(
        "sort_order", "name"
    )


def department_memberships(workspace_id, user_ids=None, exclude_group_id=None):
    """
    The memberships of active departments of the workspace, for the given people (everybody when None).

    Only the direct members of a department count: belonging to a group below a department does not make it
    the person's department.
    """
    memberships = UserGroupMember.objects.filter(
        workspace_id=workspace_id,
        group__kind=GroupKind.DEPARTMENT,
        group__is_active=True,
        group__deleted_at__isnull=True,
    )
    if user_ids is not None:
        memberships = memberships.filter(user_id__in=list(user_ids))
    if exclude_group_id is not None:
        memberships = memberships.exclude(group_id=exclude_group_id)
    return memberships


def department_map(workspace_id, user_ids=None):
    """Who works in which department: ``{user id: department (group) id}`` for the people who have one."""
    rows = department_memberships(workspace_id, user_ids).order_by("created_at").values_list("user_id", "group_id")
    found = {}
    for user_id, group_id in rows:
        # The rules keep one per person; should data from before them hold two, the oldest membership counts
        found.setdefault(user_id, group_id)
    return found


def department_of(workspace_id, user_id):
    """The active department a person belongs to, or None."""
    group_id = department_map(workspace_id, [user_id]).get(user_id)
    return UserGroup.objects.filter(pk=group_id).first() if group_id else None


def check_one_department(group, user_ids):
    """
    Raise DepartmentError when putting these people in ``group`` (or keeping them there, when it becomes an active
    department) would give any of them a second active department. Nothing to check for a plain or switched-off
    group. The message names the people and the department they already have.
    """
    if group.kind != GroupKind.DEPARTMENT or not group.is_active:
        return
    clashes = (
        department_memberships(group.workspace_id, user_ids, exclude_group_id=group.id)
        .select_related("user", "group")
        .order_by("user__display_name", "group__name")
    )
    seen, names = set(), []
    for membership in clashes:
        if membership.user_id in seen:
            continue
        seen.add(membership.user_id)
        person = membership.user.display_name or membership.user.email
        names.append(f"{person} ({membership.group.name})")
    if names:
        raise DepartmentError(
            "A person belongs to at most one department. Already in another department: " + ", ".join(names) + "."
        )
