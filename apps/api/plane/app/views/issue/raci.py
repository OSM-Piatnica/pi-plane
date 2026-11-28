# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI on a work item: the role each department has on it."""

# Python imports
import json

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission, issue_hidden_from_guest
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import Issue, Project
from plane.utils.host import base_host
from plane.utils.raci import (
    RACI_DISABLED_MESSAGE,
    RACI_EDIT_MESSAGE,
    RaciError,
    can_edit_raci,
    clean_raci,
    issue_raci,
    project_raci_enabled,
    raci_changes,
    set_issue_raci,
)


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


class IssueRaciEndpoint(BaseAPIView):
    """
    GET reads the roles of the departments on a work item, PUT replaces them all in one call.

    Both answer ``{"raci": [{"group_id", "role"}], "can_edit": bool}``. PUT takes ``{"raci": [...]}`` in the same
    shape; a department that is left out loses its role, and an empty list clears the work item.
    """

    def _load(self, request, slug, project_id, issue_id):
        """(project, work item, error): the error is the answer to give when the roles cannot be reached."""
        project = get_object_or_404(Project.objects.select_related("workspace"), workspace__slug=slug, pk=project_id)
        if not project_raci_enabled(project):
            return project, None, _error(RACI_DISABLED_MESSAGE)
        # Whoever cannot see the work item cannot see who answers for it
        if issue_hidden_from_guest(request, slug, project_id, issue_id):
            return project, None, _error("You are not allowed to view this work item.", status.HTTP_403_FORBIDDEN)
        issue = get_object_or_404(Issue, workspace__slug=slug, project_id=project_id, pk=issue_id)
        return project, issue, None

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id):
        project, issue, error = self._load(request, slug, project_id, issue_id)
        if error:
            return error
        return Response(
            {"raci": issue_raci(issue.id), "can_edit": can_edit_raci(request.user, project)},
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def put(self, request, slug, project_id, issue_id):
        project, issue, error = self._load(request, slug, project_id, issue_id)
        if error:
            return error
        if not can_edit_raci(request.user, project):
            return _error(RACI_EDIT_MESSAGE, status.HTTP_403_FORBIDDEN)
        entries = request.data.get("raci") if isinstance(request.data, dict) else None
        try:
            wanted = clean_raci(project.workspace_id, issue.id, entries)
        except RaciError as exc:
            return _error(exc.public_message)

        before, after = set_issue_raci(issue, wanted, actor=request.user)
        if raci_changes(before, after):
            # no notification here: who hears about what, by role, is decided by the notification settings of RACI
            issue_activity.delay(
                type="raci.activity.updated",
                requested_data=json.dumps({"raci": after}, cls=DjangoJSONEncoder),
                current_instance=json.dumps({"raci": before}, cls=DjangoJSONEncoder),
                actor_id=str(request.user.id),
                issue_id=str(issue.id),
                project_id=str(project_id),
                epoch=int(timezone.now().timestamp()),
                notification=False,
                origin=base_host(request=request, is_app=True),
            )
        return Response({"raci": after, "can_edit": True}, status=status.HTTP_200_OK)
