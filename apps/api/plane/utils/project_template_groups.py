# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The groups a project template makes members of the projects created from it."""

from plane.db.models import ProjectGroup, ProjectGroupRole, UserGroup
from plane.utils.project_groups import reconcile_project


def apply_template_groups(project, payload, created_by_id=None) -> dict:
    """
    Link the groups of a template payload to a new project, then let them bring their people.

    Groups that no longer exist in the workspace (deleted after the template was saved) are skipped and reported as
    {"group": id, "path": text}. Returns {"applied": n, "skipped": [...]}.
    """
    entries = payload.get("groups") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return {"applied": 0, "skipped": []}

    live = {
        str(pk)
        for pk in UserGroup.objects.filter(
            workspace_id=project.workspace_id,
            id__in=[str(e.get("group")) for e in entries if isinstance(e, dict) and e.get("group")],
        ).values_list("id", flat=True)
    }
    linked = {str(pk) for pk in ProjectGroup.objects.filter(project=project).values_list("group_id", flat=True)}
    applied = 0
    skipped = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        group_id = str(entry.get("group") or "")
        role = entry.get("role")
        if role not in ProjectGroupRole.values:
            continue
        if group_id not in live:
            skipped.append({"group": group_id or None, "path": str(entry.get("path") or "")})
            continue
        if group_id in linked:
            continue
        # `ProjectGroup.save()` validates the role; a bulk insert would not
        ProjectGroup(
            project=project,
            workspace_id=project.workspace_id,
            group_id=group_id,
            role=role,
            created_by_id=created_by_id,
        ).save()
        linked.add(group_id)
        applied += 1
    if applied:
        reconcile_project(project.id)
    return {"applied": applied, "skipped": skipped}
