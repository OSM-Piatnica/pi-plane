# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Progress of initiatives and goals, rolled up from their projects for one person.

An initiative counts the work items of its projects by state group; a goal counts the projects of all its
initiatives, each project once. Epics are left out (``Issue.progress_objects``), or their work would count twice.

A person only gets numbers from the projects whose work items they may see (``project_access``; a workspace admin
sees them all). The other projects
are left out of the numbers and of the lists, and only their count is given, so neither their names nor their sizes
leak. An archived project stays linked and listed, but its work items do not count.

A second figure, ``epic_progress``, counts the child work items of the linked Epics that the person may see. It is
kept apart from ``progress``: an Epic inside a linked project would otherwise count twice.
"""

import uuid
from collections import defaultdict

from django.db.models import Count

from plane.db.models import (
    Initiative,
    InitiativeEpic,
    InitiativeKind,
    InitiativeProject,
    Issue,
    Project,
    ProjectMember,
    WorkspaceMember,
)
from plane.db.models.project import ROLE
from plane.utils.workspace_features import is_workspace_feature_enabled

STATE_GROUPS = ("backlog", "unstarted", "started", "completed", "cancelled")


def empty_progress():
    return {"total_issues": 0, **{group: 0 for group in STATE_GROUPS}}


def project_access(user, workspace_id, project_ids=None):
    """(viewable, manageable): the projects whose work items the person may see, and the ones they may link.

    Narrowed to ``project_ids`` when given.

    * A workspace admin sees and links every project of the workspace, member of it or not.
    * Anybody else sees the work items of a project as an active member above Guest, and as a project guest only
      when the project shows everything to guests (``guest_view_all_features``); other guests see only their own
      work items, so the totals of the project are not theirs to see.
    * Anybody else links and unlinks a project (and its Epics) with at least the Member role in it. Seeing a
      project is not enough.
    """
    if WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member=user, is_active=True, role=ROLE.ADMIN.value
    ).exists():
        projects = Project.objects.filter(workspace_id=workspace_id)
        if project_ids is not None:
            projects = projects.filter(pk__in=project_ids)
        every = set(projects.values_list("id", flat=True))
        return every, set(every)

    memberships = ProjectMember.objects.filter(
        workspace_id=workspace_id,
        member=user,
        is_active=True,
        project__deleted_at__isnull=True,
    )
    if project_ids is not None:
        memberships = memberships.filter(project_id__in=project_ids)
    viewable, manageable = set(), set()
    for project_id, role, guests_see_all in memberships.values_list(
        "project_id", "role", "project__guest_view_all_features"
    ):
        if role > ROLE.GUEST.value:
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


def initiative_ids_of_projects(user, workspace_id, project_ids):
    """{project_id: [initiative ids]}: the initiatives each project is linked to, for the project list.

    Empty while the Initiatives feature is switched off, and for a workspace guest (the initiative endpoints refuse
    guests). Otherwise only the projects whose work items the person may see (``project_access``) carry their
    initiatives, as in ``project_ids`` of an initiative: where a project is linked is not told to people who may not
    see the project's numbers. Goals are not listed; a goal is reached through its initiatives (``parent``).

    A fixed number of queries, whatever the number of projects.
    """
    project_ids = set(project_ids)
    if not project_ids or not is_workspace_feature_enabled(workspace_id, "initiatives"):
        return {}
    if not WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member=user, is_active=True, role__gt=ROLE.GUEST.value
    ).exists():
        return {}
    visible = accessible_project_ids(user, workspace_id, project_ids)
    if not visible:
        return {}
    linked = defaultdict(list)
    for project_id, initiative_id in (
        InitiativeProject.objects.filter(
            workspace_id=workspace_id,
            project_id__in=visible,
            initiative__deleted_at__isnull=True,
        )
        .order_by("initiative__sort_order", "-initiative__created_at")
        .values_list("project_id", "initiative_id")
    ):
        linked[project_id].append(initiative_id)
    return linked


def add_initiative_ids(user, workspace_id, rows):
    """Add ``initiative_ids`` (see ``initiative_ids_of_projects``) to every row (a dict with an ``id``)."""
    rows = list(rows)
    linked = initiative_ids_of_projects(user, workspace_id, {row["id"] for row in rows})
    for row in rows:
        row["initiative_ids"] = [str(initiative_id) for initiative_id in linked.get(_as_uuid(row["id"]), [])]
    return rows


def _as_uuid(value):
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


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


def epic_child_state_counts(epic_ids, user, workspace_id, checked, visible):
    """The child work items of the given Epics by state group, in the projects the person may see.

    Returns ``({epic_id: {state_group: number}}, epic ids with children in projects the person may not see)``.
    The children are the direct ones, counted like project progress (``Issue.progress_objects``: no Epics, reviews,
    archived work items, drafts or triage). ``checked`` are the projects whose access is already known and
    ``visible`` the ones of them the person may see; a child in another project costs one more query, once.
    """
    counts = defaultdict(dict)
    with_hidden = set()
    if not epic_ids:
        return counts, with_hidden
    rows = list(
        Issue.progress_objects.filter(workspace_id=workspace_id, parent_id__in=epic_ids)
        .values("parent_id", "project_id", "state__group")
        .annotate(number=Count("id"))
        .order_by()
    )
    unknown = {row["project_id"] for row in rows} - set(checked)
    visible = set(visible) | (accessible_project_ids(user, workspace_id, unknown) if unknown else set())
    for row in rows:
        if row["project_id"] not in visible:
            with_hidden.add(row["parent_id"])
            continue
        epic_counts = counts[row["parent_id"]]
        epic_counts[row["state__group"]] = epic_counts.get(row["state__group"], 0) + row["number"]
    return counts, with_hidden


def roll_up_epics(epic_ids, hidden_epic_count, counts, with_hidden):
    """The Epic figure of one initiative or goal: the child work items of its visible Epics, each Epic once.

    It is partial when Epics are hidden from the person (``hidden_epic_count``) or when a visible Epic has children
    in a project the person may not see.
    """
    progress = empty_progress()
    epic_ids = list(dict.fromkeys(epic_ids))
    for epic_id in epic_ids:
        for group, number in counts.get(epic_id, {}).items():
            if group in progress:
                progress[group] += number
                progress["total_issues"] += number
    return {
        "epic_progress": progress,
        "epic_progress_is_partial": hidden_epic_count > 0 or any(epic_id in with_hidden for epic_id in epic_ids),
    }


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
    checked, visible = set(every_project), set(accessible)
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
        checked |= epic_projects
        visible |= epic_accessible

    visible_epics = {epic_id for epic_ids in epics.values() for epic_id in epic_ids}
    epic_counts, with_hidden_children = epic_child_state_counts(visible_epics, user, workspace_id, checked, visible)

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
            **roll_up_epics(epic_ids, len(hidden), epic_counts, with_hidden_children),
        }
    return described


def linked_epics(initiative, user, workspace_id):
    """The linked Epics of an initiative (of its initiatives for a goal) that the person may see, with the progress
    of each one's child work items. In the order of ``epic_ids``."""
    epic_ids = describe([initiative], user, workspace_id)[initiative.id]["epic_ids"]
    if not epic_ids:
        return []
    rows = {
        row["id"]: row
        for row in Issue.objects.filter(workspace_id=workspace_id, pk__in=epic_ids).values(
            "id",
            "name",
            "sequence_id",
            "project_id",
            "project__identifier",
            "state_id",
            "state__group",
            "target_date",
        )
    }
    projects = {row["project_id"] for row in rows.values()}
    counts, with_hidden = epic_child_state_counts(set(rows), user, workspace_id, projects, projects)
    result = []
    for epic_id in epic_ids:
        row = rows.get(epic_id)
        if row is None:
            continue
        figure = roll_up_epics([epic_id], 0, counts, with_hidden)
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "sequence_id": row["sequence_id"],
                "project_id": row["project_id"],
                "project_identifier": row["project__identifier"],
                "state_id": row["state_id"],
                "state_group": row["state__group"],
                "target_date": row["target_date"],
                "progress": figure["epic_progress"],
                "progress_is_partial": figure["epic_progress_is_partial"],
            }
        )
    return result
