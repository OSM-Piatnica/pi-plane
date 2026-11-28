# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
RACI notifications: which departments hear about which events on a work item, by their role on it (SPEC-02).

A workspace keeps a matrix of events by roles (``RaciNotificationSetting``); the defaults are the table of SPEC-02.
When something happens on a work item of a project with RACI on, the people of every department whose role the
matrix ticks for that event are told about it, next to the subscribers, assignees and mentioned people who were
told before. Nobody is told twice, the person who made the change is not told, and only active members of the
project are told, as with subscribers.

The people of a department are the direct members of an active department group; a department that is switched
off keeps its roles but tells nobody. A person in several departments is told when any of them qualifies, so this
does not rely on one department per person (decision 13, #508).

Events and the activities they come from:

* ``new_version``: an attachment is added (a draft version of a file, until acceptance brings versions);
* ``comment``: a comment is added;
* ``approval_requested`` and ``approval_decided``: approval steps of acceptance (workstream C). Nothing sends them
  yet; acceptance calls ``raci_recipient_ids`` with them;
* ``completed``: the state moves to a state of the completed group (the final version);
* ``state_or_due_date``: the state or the due date (``target_date``) changes. A move to a completed state is both
  this event and ``completed``.

Other changes (name, priority, dates of the schedule, ...) reach subscribers and assignees only, as before.
"""

from collections import defaultdict

from plane.db.models import GroupKind, IssueRaci, ProjectMember, RaciNotificationSetting, RaciRole, State
from plane.utils.departments import department_memberships
from plane.utils.raci import project_raci_enabled

ROLES = tuple(RaciRole.values)

NEW_VERSION = "new_version"
COMMENT = "comment"
APPROVAL_REQUESTED = "approval_requested"
APPROVAL_DECIDED = "approval_decided"
COMPLETED = "completed"
STATE_OR_DUE_DATE = "state_or_due_date"

RESPONSIBLE, APPROVER, CONSULTED, INFORMED = (
    RaciRole.RESPONSIBLE.value,
    RaciRole.APPROVER.value,
    RaciRole.CONSULTED.value,
    RaciRole.INFORMED.value,
)

# The events in the order they are listed, with the roles SPEC-02 gives them
DEFAULT_MATRIX = {
    NEW_VERSION: (RESPONSIBLE, CONSULTED),
    COMMENT: (RESPONSIBLE, CONSULTED),
    APPROVAL_REQUESTED: (RESPONSIBLE, APPROVER),
    APPROVAL_DECIDED: (RESPONSIBLE, APPROVER, CONSULTED),
    COMPLETED: (RESPONSIBLE, APPROVER, CONSULTED, INFORMED),
    STATE_OR_DUE_DATE: (RESPONSIBLE, CONSULTED, INFORMED),
}
EVENTS = tuple(DEFAULT_MATRIX)

SENDER = "in_app:issue_activities:raci"

MATRIX_ERRORS = {
    "not_an_object": "The matrix maps each event to the list of roles that hear about it.",
    "unknown_event": f"Unknown event. The events are: {', '.join(EVENTS)}.",
    "not_a_list": "Each event takes a list of roles.",
    "unknown_role": f"Unknown role. The roles are: {', '.join(ROLES)}.",
}


class RaciMatrixError(ValueError):
    """A matrix that cannot be stored; ``code`` keys the fixed text in ``MATRIX_ERRORS`` shown to the asker."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code

    @property
    def public_message(self):
        return MATRIX_ERRORS.get(self.code, "These notification settings cannot be saved.")


def _ordered_roles(roles):
    present = set(roles)
    return [role for role in ROLES if role in present]


def normalize_matrix(stored):
    """
    The full matrix ``{event: [roles]}`` in the order of ``EVENTS`` and ``ROLES``, from what a workspace stored.

    An event that is not stored, or not stored as a list, keeps its default; unknown events and roles are dropped.
    """
    stored = stored if isinstance(stored, dict) else {}
    matrix = {}
    for event, default in DEFAULT_MATRIX.items():
        roles = stored.get(event)
        matrix[event] = _ordered_roles(roles if isinstance(roles, list) else default)
    return matrix


def clean_matrix(data):
    """Check a requested matrix (all events or some of them) and return it as ``{event: [roles]}``."""
    if not isinstance(data, dict):
        raise RaciMatrixError("not_an_object")
    cleaned = {}
    for event, roles in data.items():
        if event not in DEFAULT_MATRIX:
            raise RaciMatrixError("unknown_event")
        if not isinstance(roles, list):
            raise RaciMatrixError("not_a_list")
        if any(role not in ROLES for role in roles):
            raise RaciMatrixError("unknown_role")
        cleaned[event] = _ordered_roles(roles)
    return cleaned


def workspace_matrix(workspace_id):
    """The matrix of a workspace, the defaults where it stored nothing."""
    row = RaciNotificationSetting.objects.filter(workspace_id=workspace_id).first()
    return normalize_matrix(row.matrix if row else {})


def save_workspace_matrix(workspace_id, changes, actor=None):
    """Store the events in ``changes`` (already cleaned) over what the workspace has; returns the full matrix."""
    row = RaciNotificationSetting.objects.filter(workspace_id=workspace_id).first()
    if row is None:
        row = RaciNotificationSetting(workspace_id=workspace_id, matrix={}, created_by=actor)
    matrix = normalize_matrix(row.matrix)
    matrix.update(changes)
    row.matrix = matrix
    row.updated_by = actor
    row.save()
    return matrix


def activity_events(activity, is_completed_state):
    """
    The events an issue activity (as the activity serializer writes it) stands for; empty for any other change.

    ``is_completed_state(state_id)`` tells whether a state belongs to the completed group.
    """
    field = activity.get("field")
    verb = activity.get("verb")
    if field == "attachment" and verb == "created":
        return (NEW_VERSION,)
    if field == "comment" and verb == "created":
        return (COMMENT,)
    if field == "state":
        state_id = activity.get("new_identifier")
        if state_id and is_completed_state(str(state_id)):
            return (COMPLETED, STATE_OR_DUE_DATE)
        return (STATE_OR_DUE_DATE,)
    if field == "target_date":
        return (STATE_OR_DUE_DATE,)
    return ()


def roles_for_events(matrix, events):
    """Every role the matrix ticks for any of the events."""
    roles = set()
    for event in events:
        roles.update(matrix.get(event, ()))
    return roles


def recipients_by_role(rows, members_by_group, roles):
    """
    The people to tell for these roles: the members of every department that has one of them.

    ``rows`` are ``(group id, role)`` of the work item, ``members_by_group`` ``{group id: {user id}}``.
    """
    people = set()
    for group_id, role in rows:
        if role in roles:
            people.update(members_by_group.get(group_id, ()))
    return people


def recipients_for_activities(activities, issue_id, rows, members_by_group, matrix, is_completed_state, exclude=()):
    """
    ``{user id: {activity id}}``: who hears about which of the activities through the role of their department.

    Activities of another work item (the other side of a relation) are left out, as are the people in ``exclude``.
    """
    excluded = {str(user_id) for user_id in exclude}
    found = defaultdict(set)
    for activity in activities or ():
        detail = activity.get("issue_detail") or {}
        if str(detail.get("id", issue_id)) != str(issue_id):
            continue
        roles = roles_for_events(matrix, activity_events(activity, is_completed_state))
        if not roles:
            continue
        for user_id in recipients_by_role(rows, members_by_group, roles):
            if str(user_id) not in excluded:
                found[user_id].add(str(activity.get("id")))
    return dict(found)


def issue_role_rows(issue_id):
    """``[(group id, role)]`` of a work item: the roles of living departments, in the order departments are listed."""
    return list(
        IssueRaci.objects.filter(issue_id=issue_id, group__kind=GroupKind.DEPARTMENT, group__deleted_at__isnull=True)
        .order_by("group__sort_order", "group__name")
        .values_list("group_id", "role")
    )


def department_members_in_project(workspace_id, project_id, group_ids):
    """``{group id: {user id}}``: the direct members of these (active) departments who are active project members."""
    project_members = ProjectMember.objects.filter(project_id=project_id, is_active=True).values("member_id")
    rows = (
        department_memberships(workspace_id)
        .filter(group_id__in=list(group_ids), user_id__in=project_members)
        .values_list("group_id", "user_id")
    )
    found = defaultdict(set)
    for group_id, user_id in rows:
        found[group_id].add(user_id)
    return dict(found)


def raci_activity_recipients(issue, activities, exclude=()):
    """
    ``{user id: {activity id}}`` for the activities of a work item: who the matrix of its workspace adds as
    recipients, and of which activities. Empty while RACI is off for the project or the work item has no roles.
    """
    project = issue.project
    if not project_raci_enabled(project):
        return {}
    rows = issue_role_rows(issue.id)
    if not rows:
        return {}
    members = department_members_in_project(project.workspace_id, project.id, {group_id for group_id, _ in rows})
    if not members:
        return {}
    completed = None

    def is_completed_state(state_id):
        nonlocal completed
        if completed is None:
            completed = {
                str(pk)
                for pk in State.all_state_objects.filter(project_id=project.id, group="completed").values_list(
                    "id", flat=True
                )
            }
        return state_id in completed

    return recipients_for_activities(
        activities, issue.id, rows, members, workspace_matrix(project.workspace_id), is_completed_state, exclude
    )


def raci_recipient_ids(issue, event, exclude=()):
    """
    The people the matrix adds as recipients of one event on a work item, for callers that make events of their
    own (acceptance: ``approval_requested``, ``approval_decided``). Empty while RACI is off for the project.
    """
    project = issue.project
    if event not in DEFAULT_MATRIX or not project_raci_enabled(project):
        return set()
    rows = issue_role_rows(issue.id)
    if not rows:
        return set()
    members = department_members_in_project(project.workspace_id, project.id, {group_id for group_id, _ in rows})
    roles = roles_for_events(workspace_matrix(project.workspace_id), (event,))
    excluded = {str(user_id) for user_id in exclude}
    return {user_id for user_id in recipients_by_role(rows, members, roles) if str(user_id) not in excluded}


def preview_events(matrix, rows, members_by_group):
    """
    For every event: the roles it reaches, the departments of the work item that have one of them (with how many
    of their people are told) and the people told. Departments in the order of ``rows``.
    """
    events = []
    for event in EVENTS:
        roles = set(matrix.get(event, ()))
        departments = []
        people = set()
        for group_id, role in rows:
            if role not in roles:
                continue
            members = members_by_group.get(group_id, set())
            people.update(members)
            departments.append({"group_id": str(group_id), "role": role, "member_count": len(members)})
        events.append(
            {
                "event": event,
                "roles": _ordered_roles(roles),
                "departments": departments,
                "member_ids": sorted(str(user_id) for user_id in people),
            }
        )
    return events


def notification_preview(issue):
    """Who the roles on a work item make hear about each event (``preview_events``), for its detail view."""
    project = issue.project
    rows = issue_role_rows(issue.id)
    members = (
        department_members_in_project(project.workspace_id, project.id, {group_id for group_id, _ in rows})
        if rows
        else {}
    )
    return preview_events(workspace_matrix(project.workspace_id), rows, members)
