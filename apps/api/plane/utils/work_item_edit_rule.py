# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: only the assignees of a work item, the project lead and the project admins may change it.

The rule is switched on per project with ``Project.is_assignee_edit_rule_enabled``. It adds to the role checks, never
replaces them: a person still needs the role the endpoint asks for. It restricts what changes the work item itself
(its fields, state, dates, assignees, deletion and archiving, sub-items, relations, links, attachments, custom
properties, cycles and modules) and leaves discussion open: comments, reactions, subscribing and time logs.

A work item without an assignee stays open to every member who may edit it, so new work can be picked up and
assigned. Administrators are the project's admins and the workspace admins who are in the project, as everywhere else.
"""

from collections import defaultdict
from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from plane.db.models import Issue, IssueAssignee, IssueGroupAssignee, Project, ProjectMember, WorkspaceMember
from plane.utils.user_groups import issue_ids_assigned_through_groups

ADMIN_ROLE = 20

WORK_ITEM_EDIT_RESTRICTED = "work_item_edit_restricted"
DENIED_MESSAGE = "Only the assignees of this work item, the project lead and project admins can change it."


def _is_project_admin(user, project):
    members = ProjectMember.objects.filter(member=user, project_id=project.id, is_active=True)
    if members.filter(role=ADMIN_ROLE).exists():
        return True
    # a workspace admin who is part of the project counts as an admin of it
    return (
        members.exists()
        and WorkspaceMember.objects.filter(
            member=user, workspace_id=project.workspace_id, role=ADMIN_ROLE, is_active=True
        ).exists()
    )


def unchangeable_issue_ids(user, project_id, issue_ids):
    """Of the work items of ``project_id`` among ``issue_ids``, those the rule keeps ``user`` from changing."""
    ids = {str(issue_id) for issue_id in issue_ids if issue_id}
    if not ids or user is None or getattr(user, "is_anonymous", True):
        return set()

    project = (
        Project.objects.filter(pk=project_id)
        .only("id", "workspace_id", "project_lead_id", "is_assignee_edit_rule_enabled")
        .first()
    )
    if project is None or not project.is_assignee_edit_rule_enabled:
        return set()
    if project.project_lead_id == user.id or _is_project_admin(user, project):
        return set()

    scoped = {str(pk) for pk in Issue.objects.filter(pk__in=ids, project_id=project_id).values_list("id", flat=True)}
    assignees = defaultdict(set)
    for issue_id, assignee_id in IssueAssignee.objects.filter(issue_id__in=scoped).values_list(
        "issue_id", "assignee_id"
    ):
        assignees[str(issue_id)].add(assignee_id)
    # a group an item is assigned to counts its members as assignees
    group_assigned = defaultdict(bool)
    for issue_id in IssueGroupAssignee.objects.filter(issue_id__in=scoped).values_list("issue_id", flat=True):
        group_assigned[str(issue_id)] = True
    through_group = {
        str(issue_id) for issue_id in issue_ids_assigned_through_groups(user, project.workspace_id, scoped)
    }
    # an item nobody is assigned to is open to everyone who may edit it
    return {
        issue_id
        for issue_id in scoped
        if (assignees[issue_id] or group_assigned[issue_id])
        and user.id not in assignees[issue_id]
        and issue_id not in through_group
    }


def work_item_edit_denied(user, project_id, issue_ids):
    """A 403 response when the rule keeps ``user`` from changing one of ``issue_ids``, else None."""
    blocked = unchangeable_issue_ids(user, project_id, issue_ids)
    if not blocked:
        return None
    return Response(
        {"error": DENIED_MESSAGE, "error_code": WORK_ITEM_EDIT_RESTRICTED, "work_item_ids": sorted(blocked)},
        status=status.HTTP_403_FORBIDDEN,
    )


def can_change_work_items(user, issues):
    """Whether ``user`` may change every one of ``issues`` (work items, possibly of several projects)."""
    by_project = defaultdict(list)
    for issue in issues:
        by_project[issue.project_id].append(issue.id)
    return all(not unchangeable_issue_ids(user, project_id, ids) for project_id, ids in by_project.items())


def _ids_from(value):
    if isinstance(value, (list, tuple, set)):
        return [item for item in value]
    return [value] if value else []


def restrict_work_item_changes(param=None, body=None):
    """Guard for a view method that changes work items.

    ``param`` names the URL argument holding the work item id (``issue_id``, ``pk``); ``body`` is a function of the
    request returning further work item ids the request changes (for example a list in its body). Put it directly
    above the method, below ``allow_permission``.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(instance, request, *args, **kwargs):
            issue_ids = _ids_from(kwargs.get(param)) if param else []
            if body is not None:
                issue_ids += _ids_from(body(request))
            denied = work_item_edit_denied(request.user, kwargs.get("project_id"), issue_ids)
            if denied is not None:
                return denied
            return view_func(instance, request, *args, **kwargs)

        return wrapped

    return decorator


def body_list(key):
    """``body`` for ``restrict_work_item_changes``: the list of ids under ``key`` of the request data."""
    return lambda request: [
        item for item in (request.data.get(key) or []) if isinstance(item, (str, int)) or hasattr(item, "hex")
    ]


def body_update_ids(request):
    """``body`` for the timeline drag: the ids of the ``updates`` list."""
    return [update.get("id") for update in (request.data.get("updates") or []) if isinstance(update, dict)]
