# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Progress of initiatives and goals, rolled up from their projects for one person.

An initiative counts the work items of its projects by state group; a goal counts the projects of all its
initiatives, each project once. Epics are left out (``Issue.progress_objects``), or their work would count twice.

A person only gets numbers from the projects they are an active member of. The projects they are not in are left
out of the numbers and of the lists, and only their count is given, so neither their names nor their sizes leak.
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
)

STATE_GROUPS = ("backlog", "unstarted", "started", "completed", "cancelled")


def empty_progress():
    return {"total_issues": 0, **{group: 0 for group in STATE_GROUPS}}


def accessible_project_ids(user, workspace_id, project_ids=None):
    """The projects of the workspace the person is an active member of (narrowed to ``project_ids`` when given)."""
    memberships = ProjectMember.objects.filter(
        workspace_id=workspace_id,
        member=user,
        is_active=True,
        project__deleted_at__isnull=True,
    )
    if project_ids is not None:
        memberships = memberships.filter(project_id__in=project_ids)
    return set(memberships.values_list("project_id", flat=True))


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

    For each one: the linked projects and Epics the person may see, how many are hidden, and the progress. For a
    goal also its initiatives. The number of queries does not grow with the number of initiatives.
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

    epics = defaultdict(list)
    hidden_epics = defaultdict(int)
    own_ids = [item.id for item in initiatives if item.kind == InitiativeKind.INITIATIVE]
    if own_ids:
        epic_rows = list(
            InitiativeEpic.objects.filter(
                workspace_id=workspace_id, initiative_id__in=own_ids, issue__deleted_at__isnull=True
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
                hidden_epics[initiative_id] += 1

    described = {}
    for item in initiatives:
        if item.kind == InitiativeKind.GOAL:
            child_ids = children.get(item.id, [])
            # A project in two initiatives of the goal is one project: the set counts it once
            project_ids = {project_id for child_id in child_ids for project_id in linked.get(child_id, [])}
            ordered = sorted((project_id for project_id in project_ids if project_id in accessible), key=str)
        else:
            child_ids = []
            project_ids = set(linked.get(item.id, []))
            ordered = [project_id for project_id in linked.get(item.id, []) if project_id in accessible]
        described[item.id] = {
            "initiative_ids": child_ids,
            "project_ids": ordered,
            "epic_ids": epics.get(item.id, []),
            "hidden_epic_count": hidden_epics.get(item.id, 0),
            **roll_up(project_ids, accessible, counts),
        }
    return described
