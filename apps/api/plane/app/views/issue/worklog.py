# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Time logged on work items (worklogs)."""

# Python imports
import json

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.worklog import IssueWorkLogSerializer
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import Issue, IssueAssignee, IssueWorkLog, Project, ProjectMember, WorkspaceMember
from plane.utils.host import base_host
from plane.utils.user_groups import issue_ids_assigned_through_groups

TIME_TRACKING_DISABLED = {"error": "Time tracking is not enabled"}


def time_tracking_enabled(slug, project_id):
    return Project.objects.filter(workspace__slug=slug, pk=project_id, is_time_tracking_enabled=True).exists()


def is_project_admin(user, slug, project_id):
    return ProjectMember.objects.filter(
        workspace__slug=slug, project_id=project_id, member=user, role=ROLE.ADMIN.value, is_active=True
    ).exists()


def can_log_time(user, slug, project_id, issue_id):
    """A project admin may log time on any work item, a member only on the ones they are assigned to."""
    if is_project_admin(user, slug, project_id):
        return True
    if IssueAssignee.objects.filter(
        workspace__slug=slug, project_id=project_id, issue_id=issue_id, assignee=user
    ).exists():
        return True
    # Belonging to a group the work item is assigned to counts as being assigned
    workspace_id = (
        Project.objects.filter(workspace__slug=slug, pk=project_id).values_list("workspace_id", flat=True).first()
    )
    return workspace_id is not None and bool(issue_ids_assigned_through_groups(user, workspace_id, [issue_id]))


def can_modify(worklog, user, slug, project_id):
    """The author, a project admin, or a workspace admin may change or remove an entry."""
    if worklog.logged_by_id == user.id:
        return True
    if is_project_admin(user, slug, project_id):
        return True
    return WorkspaceMember.objects.filter(
        workspace__slug=slug, member=user, role=ROLE.ADMIN.value, is_active=True
    ).exists()


def log_activity(request, activity_type, issue_id, project_id, requested_data, current_instance=None):
    # no notification: a time entry is not news for everyone who follows the work item
    issue_activity.delay(
        type=activity_type,
        requested_data=json.dumps(requested_data, cls=DjangoJSONEncoder),
        actor_id=str(request.user.id),
        issue_id=str(issue_id),
        project_id=str(project_id),
        current_instance=current_instance,
        epoch=int(timezone.now().timestamp()),
        notification=False,
        origin=base_host(request=request, is_app=True),
    )


class IssueWorkLogsEndpoint(BaseAPIView):
    """GET lists the entries of a work item with their total, POST logs time on it."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id, issue_id):
        if not time_tracking_enabled(slug, project_id):
            return Response(TIME_TRACKING_DISABLED, status=status.HTTP_400_BAD_REQUEST)
        get_object_or_404(Issue, workspace__slug=slug, project_id=project_id, pk=issue_id)
        worklogs = IssueWorkLog.objects.filter(workspace__slug=slug, project_id=project_id, issue_id=issue_id)
        total = worklogs.aggregate(total_duration=Sum("duration"))["total_duration"] or 0
        return Response(
            {"worklogs": IssueWorkLogSerializer(worklogs, many=True).data, "total_duration": total},
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, issue_id):
        if not time_tracking_enabled(slug, project_id):
            return Response(TIME_TRACKING_DISABLED, status=status.HTTP_400_BAD_REQUEST)
        # scope the work item to the project before anything is written
        issue = get_object_or_404(Issue, workspace__slug=slug, project_id=project_id, pk=issue_id)
        if not can_log_time(request.user, slug, project_id, issue_id):
            return Response(
                {"error": "Only a project admin or an assignee can log time on this work item"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = IssueWorkLogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # whom the time is logged for is never taken from the request
        worklog = serializer.save(issue=issue, project_id=project_id, workspace=issue.workspace, logged_by=request.user)
        log_activity(request, "worklog.activity.created", issue_id, project_id, {"duration": worklog.duration})
        return Response(IssueWorkLogSerializer(worklog).data, status=status.HTTP_201_CREATED)


class IssueWorkLogDetailEndpoint(BaseAPIView):
    """PATCH changes and DELETE removes one entry (its author, or an admin)."""

    def get_worklog(self, slug, project_id, issue_id, pk):
        return get_object_or_404(IssueWorkLog, workspace__slug=slug, project_id=project_id, issue_id=issue_id, pk=pk)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def patch(self, request, slug, project_id, issue_id, pk):
        if not time_tracking_enabled(slug, project_id):
            return Response(TIME_TRACKING_DISABLED, status=status.HTTP_400_BAD_REQUEST)
        worklog = self.get_worklog(slug, project_id, issue_id, pk)
        if not can_modify(worklog, request.user, slug, project_id):
            return Response(
                {"error": "Only the author or a project admin can edit this entry"}, status=status.HTTP_403_FORBIDDEN
            )
        current_instance = json.dumps(IssueWorkLogSerializer(worklog).data, cls=DjangoJSONEncoder)
        serializer = IssueWorkLogSerializer(worklog, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        worklog = serializer.save()
        log_activity(
            request,
            "worklog.activity.updated",
            issue_id,
            project_id,
            {"duration": worklog.duration},
            current_instance=current_instance,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, issue_id, pk):
        if not time_tracking_enabled(slug, project_id):
            return Response(TIME_TRACKING_DISABLED, status=status.HTTP_400_BAD_REQUEST)
        worklog = self.get_worklog(slug, project_id, issue_id, pk)
        if not can_modify(worklog, request.user, slug, project_id):
            return Response(
                {"error": "Only the author or a project admin can delete this entry"},
                status=status.HTTP_403_FORBIDDEN,
            )
        duration = worklog.duration
        worklog.delete()
        log_activity(request, "worklog.activity.deleted", issue_id, project_id, {"duration": duration})
        return Response(status=status.HTTP_204_NO_CONTENT)
