# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Who may see the time logged on work items."""

from plane.db.models import ProjectMember, WorkspaceMember

# Project roles (see plane.app.permissions.ROLE): admin and member
READER_ROLES = (20, 15)
WORKSPACE_ADMIN_ROLE = 20


def can_view_worklogs(user, slug, project_id):
    """Time logged on work items is confidential: project admins and members see it, guests do not.

    A workspace admin sees it whatever their role in the project is.
    """
    project_role = (
        ProjectMember.objects.filter(project_id=project_id, workspace__slug=slug, member=user, is_active=True)
        .values_list("role", flat=True)
        .first()
    )
    if project_role in READER_ROLES:
        return True
    return WorkspaceMember.objects.filter(
        workspace__slug=slug, member=user, role=WORKSPACE_ADMIN_ROLE, is_active=True
    ).exists()
