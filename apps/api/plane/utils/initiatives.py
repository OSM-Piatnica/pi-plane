# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Progress of initiatives and goals, rolled up from their projects for one person.

An initiative counts the work items of its projects by state group; a goal counts the projects of all its
initiatives, each project once. Epics are left out (``Issue.progress_objects``), or their work would count twice.

A person only gets numbers from the projects whose work items they may see (``project_access``). The other projects
are left out of the numbers and of the lists, and only their count is given, so neither their names nor their sizes
leak. An archived project stays linked and listed, but its work items do not count.
"""

from collections import defaultdict

from django.db.models import Count

from plane.db.models import (
    Initiative,
    InitiativeEpic,
    InitiativeKind,
    InitiativeProject,
    Issue,
    ProjectMember,
    WorkspaceMember,
)
from plane.db.models.project import ROLE

STATE_GROUPS = ("backlog", "unstarted", "started", "completed", "cancelled")


def empty_progress():
    return {"total_issues": 0, **{group: 0 for group in STATE_GROUPS}}


def project_access(user, workspace_id, project_ids=None):
    """(viewable, manageable): the projects whose work items the person may see, and the ones they may link.

    Narrowed to ``project_ids`` when given. The rules of the rest of the app:

    * work items are seen by an active project member above Guest, and by a project guest only when the project
      shows everything to guests (``guest_view_all_features``); other guests see only their own work items, so the
      totals of the project are not theirs to see;
    * linking and unlinking takes at least the Member role in the project;
    * a workspace admin with any active membership of the project counts as its admin; one who is not in the
      project has no access to it.
    """
    memberships = ProjectMember.objects.filter(
        workspace_id=workspace_id,
        member=user,
        is_active=True,
        project__deleted_at__isnull=True,
    )
    if project_ids is not None:
        memberships = memberships.filter(project_id__in=project_ids)
    rows = list(memberships.values_list("project_id", "role", "project__guest_view_all_features"))
    workspace_admin = bool(rows) and (
        WorkspaceMember.objects.filter(
            workspace_id=workspace_id, member=user, is_active=True, role=ROLE.ADMIN.value
        ).exists()
    )
    viewable, manageable = set(), set()
    for project_id, role, guests_see_all in rows:
        if workspace_admin or role > ROLE.GUEST.value:
            viewable.add(project_id)
            manageable.add(project_id)
        elif guests_see_all:
            viewable.add(project_id)
    return viewable, manageable


def accessible_project_ids(user, workspace_id, project_ids=None):
    """The projects whose work items the person may see (see ``project_access``)."""
    return project_access(user, workspace_id, project_ids)[0]


def manageable_project_ids(user, workspace_id, project_ids=None):
    """The projects the person may link to an initiative or unlink from it (see ``project_access``)."""
    return project_access(user, workspace_id, project_ids)[1]


def roll_up(project_ids, accessible, counts):
    """The progress of one initiative or goal.

    ``project_ids`` are its linked projects (for a goal: of all its initiatives, so a set counts each one once),
    ``accessible`` the projects the person may see, ``counts`` is {project_id: {state_group: number}}.
    """
    project_ids = set(project_ids)
    visible = project_ids & accessible
    progress = empty_progress()
    for project_id in visible:
        for group, number in counts.get(project_id, {}).items():
            if group in progress:
                progress[group] += number
                progress["total_issues"] += number
    hidden = len(project_ids - visible)
    return {
        "progress": progress,
        "progress_is_partial": hidden > 0,
        "hidden_project_count": hidden,
    }


def project_state_counts(project_ids):
    """{project_id: {state_group: number of work items}} for the given projects, in one query."""
    counts = defaultdict(dict)
    if not project_ids:
        return counts
    rows = (
        Issue.progress_objects.filter(project_id__in=project_ids)
        .values("project_id", "state__group")
        .annotate(number=Count("id"))
        .order_by()
    )
    for row in rows:
        counts[row["project_id"]][row["state__group"]] = row["number"]
    return counts


def describe(initiatives, user, workspace_id):
    """What the API adds to each initiative for this person: {initiative_id: {...}}.

    For each one: the linked projects and Epics the person may see, how many are hidden, and the progress. A goal
    has the projects and Epics of its initiatives, each once, and the list of those initiatives. The
    number of queries does not grow with the number of initiatives.
    """
    initiatives = list(initiatives)
    goal_ids = [item.id for item in initiatives if item.kind == InitiativeKind.GOAL]

    children = defaultdict(list)
    if goal_ids:
        for child_id, parent_id in (
            Initiative.objects.filter(workspace_id=workspace_id, parent_id__in=goal_ids)
            .order_by("sort_order", "-created_at")
            .values_list("id", "parent_id")
        ):
            children[parent_id].append(child_id)

    wanted = {item.id for item in initiatives}
    for child_ids in children.values():
        wanted.update(child_ids)

    linked = defaultdict(list)
    for initiative_id, project_id in (
        InitiativeProject.objects.filter(
            workspace_id=workspace_id, initiative_id__in=wanted, project__deleted_at__isnull=True
        )
        .order_by("created_at")
        .values_list("initiative_id", "project_id")
    ):
        linked[initiative_id].append(project_id)

    every_project = {project_id for project_ids in linked.values() for project_id in project_ids}
    accessible = accessible_project_ids(user, workspace_id, every_project) if every_project else set()
    counts = project_state_counts(every_project & accessible)

    # Per initiative: the visible Epics in the order they were linked, and the hidden ones
    epics = defaultdict(list)
    hidden_epics = defaultdict(set)
    if wanted:
        epic_rows = list(
            InitiativeEpic.objects.filter(
                workspace_id=workspace_id,
                initiative_id__in=wanted,
                # A link whose work item is no longer an Epic, or is archived, is not shown (it can still be removed)
                issue__type__is_epic=True,
                issue__deleted_at__isnull=True,
                issue__archived_at__isnull=True,
                issue__project__deleted_at__isnull=True,
                issue__project__archived_at__isnull=True,
            )
            .order_by("created_at")
            .values_list("initiative_id", "issue_id", "issue__project_id")
        )
        epic_projects = {project_id for _, _, project_id in epic_rows}
        unknown = epic_projects - every_project
        epic_accessible = (accessible & epic_projects) | (
            accessible_project_ids(user, workspace_id, unknown) if unknown else set()
        )
        for initiative_id, issue_id, project_id in epic_rows:
            if project_id in epic_accessible:
                epics[initiative_id].append(issue_id)
            else:
                hidden_epics[initiative_id].add(issue_id)

    described = {}
    for item in initiatives:
        if item.kind == InitiativeKind.GOAL:
            child_ids = children.get(item.id, [])
            # A project in two initiatives of the goal is one project: the set counts it once
            project_ids = {project_id for child_id in child_ids for project_id in linked.get(child_id, [])}
            ordered = sorted((project_id for project_id in project_ids if project_id in accessible), key=str)
            # The same for an Epic linked to two of them; dict.fromkeys keeps the first place of each
            epic_ids = list(dict.fromkeys(epic_id for child_id in child_ids for epic_id in epics.get(child_id, [])))
            hidden = {epic_id for child_id in child_ids for epic_id in hidden_epics.get(child_id, ())}
        else:
            child_ids = []
            project_ids = set(linked.get(item.id, []))
            ordered = [project_id for project_id in linked.get(item.id, []) if project_id in accessible]
            epic_ids = epics.get(item.id, [])
            hidden = hidden_epics.get(item.id, ())
        described[item.id] = {
            "initiative_ids": child_ids,
            "project_ids": ordered,
            "epic_ids": epic_ids,
            "hidden_epic_count": len(hidden),
            **roll_up(project_ids, accessible, counts),
        }
    return described
