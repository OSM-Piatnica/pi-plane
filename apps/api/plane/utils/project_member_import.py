# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Import the members of a project from the rows of a CSV file.

A row names either a person (``email``) or a group (``group``: its name, or its path ``Parent / Child``) and a role.
People are added as direct members, brought back when they were removed, and left alone when they already are members.
Groups are linked to the project (or their role is changed) as project groups, which only ever are Members or Guests.
Rows that cannot be applied are skipped and reported with a code and a reason; nothing is created beyond the links
and memberships the rows ask for (never users, never groups).
"""

from dataclasses import dataclass, field

from plane.db.models import (
    ProjectGroup,
    ProjectGroupRole,
    ProjectMember,
    WorkspaceMember,
)
from plane.utils.group_paths import find_group, index_groups, is_ambiguous
from plane.utils.project_groups import _ensure_properties, reconcile_project

MAX_ROWS = 5000
ROLES = (5, 15, 20)

REASONS = {
    "invalid_role": "The role must be 5 (Guest), 15 (Member) or 20 (Admin).",
    "both_email_and_group": "A row has either an Email or a Group, not both.",
    "missing_value": "The row has neither an Email nor a Group.",
    "not_workspace_member": "This person is not an active member of the workspace.",
    "role_above_workspace_role": "The role is higher than the person's workspace role.",
    "role_below_workspace_role": "The role is lower than the person's workspace role.",
    "unknown_group": "No group with this name exists in the workspace.",
    "ambiguous_group": "Several groups have this name, write its path as Parent / Child.",
    "group_admin_role": "Groups cannot be project admins.",
    "group_already_linked": "The group already is a member of the project with this role.",
}


def _role_of(value):
    try:
        role = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return role if role in ROLES else None


def _text(value):
    return value.strip() if isinstance(value, str) else ("" if value is None else str(value).strip())


@dataclass
class ImportResult:
    people: dict = field(default_factory=lambda: {"added": 0, "reactivated": 0, "already_members": 0, "skipped": 0})
    groups: dict = field(default_factory=lambda: {"added": 0, "updated": 0, "skipped": 0})
    skipped: list = field(default_factory=list)

    def skip(self, kind, row, value, code):
        self.skipped.append({"row": row, "type": kind, "value": value, "code": code, "reason": REASONS[code]})
        (self.people if kind == "person" else self.groups)["skipped"] += 1

    def as_dict(self):
        return {"people": self.people, "groups": self.groups, "skipped": self.skipped}


def import_project_members(project, rows):
    """Apply the rows to the project. Returns ``(summary dict, ids of the people added or brought back)``."""
    workspace_id = project.workspace_id
    result = ImportResult()
    people = {}
    for item in WorkspaceMember.objects.filter(workspace_id=workspace_id, is_active=True, member__is_bot=False).values(
        "member_id", "role", "member__email"
    ):
        people[(item["member__email"] or "").strip().casefold()] = (item["member_id"], item["role"])
    members = {row.member_id: row for row in ProjectMember.objects.filter(project_id=project.id)}
    links = {link.group_id: link for link in ProjectGroup.objects.filter(project_id=project.id)}
    by_path, by_name = index_groups(workspace_id)

    to_create = []
    to_update = {}
    new_rows = {}
    reconcile = False

    for index, raw in enumerate(rows):
        row = raw.get("row") if isinstance(raw.get("row"), int) else index + 1
        email = _text(raw.get("email")).casefold()
        group_name = _text(raw.get("group"))
        role = _role_of(raw.get("role"))
        if email and group_name:
            result.skip("person", row, f"{email} / {group_name}", "both_email_and_group")
            continue
        if not email and not group_name:
            result.skip("person", row, "", "missing_value")
            continue

        if group_name:
            if role is None:
                result.skip("group", row, group_name, "invalid_role")
                continue
            if role not in ProjectGroupRole.values:
                result.skip("group", row, group_name, "group_admin_role")
                continue
            group_id = find_group(group_name, by_path, by_name)
            if group_id is None and is_ambiguous(group_name, by_name):
                result.skip("group", row, group_name, "ambiguous_group")
                continue
            if group_id is None:
                result.skip("group", row, group_name, "unknown_group")
                continue
            link = links.get(group_id)
            if link is None:
                links[group_id] = ProjectGroup.objects.create(
                    project_id=project.id, workspace_id=workspace_id, group_id=group_id, role=role
                )
                result.groups["added"] += 1
            elif link.role == role:
                result.skip("group", row, group_name, "group_already_linked")
                continue
            else:
                link.role = role
                link.save(update_fields=["role", "updated_at"])
                result.groups["updated"] += 1
            reconcile = True
            continue

        if role is None:
            result.skip("person", row, email, "invalid_role")
            continue
        found = people.get(email)
        if found is None:
            result.skip("person", row, email, "not_workspace_member")
            continue
        user_id, workspace_role = found
        if workspace_role == 20 and role in (5, 15):
            result.skip("person", row, email, "role_below_workspace_role")
            continue
        if workspace_role == 5 and role in (15, 20):
            result.skip("person", row, email, "role_above_workspace_role")
            continue
        if user_id in new_rows:
            result.people["already_members"] += 1
            continue
        existing = members.get(user_id)
        if existing is None:
            member = ProjectMember(
                workspace_id=workspace_id, project_id=project.id, member_id=user_id, role=role, is_active=True
            )
            to_create.append(member)
            new_rows[user_id] = member
            result.people["added"] += 1
        elif not existing.is_active:
            existing.is_active = True
            existing.role = role
            existing.via_group = False
            existing.group_role = None
            existing.direct_role = None
            to_update[user_id] = existing
            new_rows[user_id] = existing
            result.people["reactivated"] += 1
            reconcile = True
        elif existing.via_group:
            # Only in through a group so far: the role given is their own now
            existing.via_group = False
            existing.role = role
            existing.direct_role = role
            to_update[user_id] = existing
            new_rows[user_id] = existing
            result.people["added"] += 1
            reconcile = True
        else:
            result.people["already_members"] += 1

    if to_create:
        ProjectMember.objects.bulk_create(to_create, batch_size=100, ignore_conflicts=True)
    if to_update:
        ProjectMember.objects.bulk_update(
            list(to_update.values()),
            ["is_active", "role", "via_group", "group_role", "direct_role"],
            batch_size=100,
        )
    if new_rows:
        _ensure_properties(workspace_id, [(user_id, project.id) for user_id in new_rows])
    if reconcile:
        reconcile_project(project.id)
    return result.as_dict(), set(new_rows)
