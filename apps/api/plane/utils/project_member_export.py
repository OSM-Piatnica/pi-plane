# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The members of a project as rows of an export file the members CSV import can read again.

One row per project group (``group`` is its path "Parent / Child", ``email`` blank) and one row per direct person
member with their own role. People who belong only through a group derive from the group rows, so they are left out
unless asked for; then they are written as ``person (via group)``, which the import skips.
"""

from plane.db.models import ProjectGroup, ProjectMember
from plane.utils.group_paths import group_paths
from plane.utils.project_groups import _groups_of_users
from plane.utils.user_groups import _parent_map

SOURCE_PERSON = "person"
SOURCE_GROUP = "group"
SOURCE_PERSON_VIA_GROUP = "person (via group)"
VIA_GROUP_SEPARATOR = "; "


def _day(value):
    return value.date().isoformat() if value else ""


def project_member_export_rows(project, include_via_group=False):
    """Rows (dicts) of the project: groups first, then people by email. Only this project's own data is read."""
    workspace_id = project.workspace_id
    paths = group_paths(workspace_id)

    links = ProjectGroup.objects.filter(project_id=project.id, group__deleted_at__isnull=True).select_related("group")
    group_rows = sorted(
        (
            {
                "email": "",
                "group": paths.get(link.group_id, link.group.name),
                "role": link.role,
                "name": link.group.name,
                "source": SOURCE_GROUP,
                "via_group": "",
                "raised_by_group": "",
                "joined": _day(link.created_at),
            }
            for link in links
        ),
        key=lambda row: row["group"].casefold(),
    )

    members = ProjectMember.objects.filter(
        project_id=project.id, is_active=True, member__isnull=False, member__is_bot=False
    ).select_related("member")
    if not include_via_group:
        members = members.filter(via_group=False)
    members = list(members)

    linked_group_ids = {link.group_id for link in links}
    through = {}
    via_ids = [member.member_id for member in members if member.via_group]
    if via_ids and linked_group_ids:
        belonging = _groups_of_users(workspace_id, via_ids, _parent_map(workspace_id))
        for user_id, groups in belonging.items():
            through[user_id] = sorted(
                (paths[group_id] for group_id in groups & linked_group_ids if group_id in paths), key=str.casefold
            )

    people_rows = []
    for member in members:
        user = member.member
        if member.via_group:
            source = SOURCE_PERSON_VIA_GROUP
            role = member.role
            via = VIA_GROUP_SEPARATOR.join(through.get(member.member_id, []))
            raised = ""
        else:
            source = SOURCE_PERSON
            # Their own role, which a group may have raised in `role`
            role = member.direct_role if member.direct_role is not None else member.role
            via = ""
            raised = "yes" if member.direct_role is not None else ""
        people_rows.append(
            {
                "email": user.email or "",
                "group": "",
                "role": role,
                "name": user.display_name or "",
                "source": source,
                "via_group": via,
                "raised_by_group": raised,
                "joined": _day(member.created_at),
            }
        )
    people_rows.sort(key=lambda row: row["email"].casefold())
    return group_rows + people_rows
