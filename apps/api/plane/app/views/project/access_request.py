# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import IntegrityError, transaction
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import ProjectAccessRequestSerializer
from plane.db.models import Project, ProjectAccessRequest, ProjectMember, ProjectUserProperty, WorkspaceMember
from plane.db.models.project import ProjectNetwork

MESSAGE_MAX_LENGTH = 500


def _visible_project(slug, project_id):
    """The project, or None when it does not exist or is Secret (its existence is not revealed here)."""
    project = Project.objects.filter(pk=project_id, workspace__slug=slug, archived_at__isnull=True).first()
    if project is None or project.network == ProjectNetwork.SECRET.value:
        return None
    return project


class ProjectAccessRequestEndpoint(BaseAPIView):
    """Request access to a Private project (any workspace member), and list its open requests (project admins)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug, project_id):
        project = _visible_project(slug, project_id)
        if project is None:
            return Response({"error": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND)
        if project.network == ProjectNetwork.PUBLIC.value:
            return Response({"error": "This project is public; join it directly"}, status=status.HTTP_400_BAD_REQUEST)
        if ProjectMember.objects.filter(project=project, member=request.user, is_active=True).exists():
            return Response({"error": "You are already a member of this project"}, status=status.HTTP_409_CONFLICT)

        message = str(request.data.get("message") or "").strip()
        if len(message) > MESSAGE_MAX_LENGTH:
            return Response(
                {"error": f"The message can have at most {MESSAGE_MAX_LENGTH} characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending = ProjectAccessRequest.objects.filter(
            project=project, requester=request.user, status=ProjectAccessRequest.PENDING
        ).first()
        if pending is not None:
            return Response(ProjectAccessRequestSerializer(pending).data, status=status.HTTP_200_OK)
        try:
            with transaction.atomic():
                access_request = ProjectAccessRequest.objects.create(
                    project=project, requester=request.user, message=message
                )
        except IntegrityError:
            # two requests at once: the other one won
            access_request = ProjectAccessRequest.objects.get(
                project=project, requester=request.user, status=ProjectAccessRequest.PENDING
            )
            return Response(ProjectAccessRequestSerializer(access_request).data, status=status.HTTP_200_OK)
        return Response(ProjectAccessRequestSerializer(access_request).data, status=status.HTTP_201_CREATED)

    @allow_permission([ROLE.ADMIN])
    def get(self, request, slug, project_id):
        access_requests = (
            ProjectAccessRequest.objects.filter(
                project_id=project_id, workspace__slug=slug, status=ProjectAccessRequest.PENDING
            )
            .select_related("requester")
            .order_by("created_at")
        )
        return Response(ProjectAccessRequestSerializer(access_requests, many=True).data, status=status.HTTP_200_OK)


class ProjectAccessRequestMineEndpoint(BaseAPIView):
    """The signed-in user's latest access request to the project, or null."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug, project_id):
        project = _visible_project(slug, project_id)
        if project is None:
            return Response({"error": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND)
        access_request = ProjectAccessRequest.objects.filter(project=project, requester=request.user).first()
        data = ProjectAccessRequestSerializer(access_request).data if access_request else None
        return Response(data, status=status.HTTP_200_OK)


class ProjectAccessRequestDetailEndpoint(BaseAPIView):
    """Approve or reject an open access request (project admins)."""

    @allow_permission([ROLE.ADMIN])
    def patch(self, request, slug, project_id, pk):
        decision = request.data.get("status")
        if decision not in (ProjectAccessRequest.APPROVED, ProjectAccessRequest.REJECTED):
            return Response({"error": "status must be 'approved' or 'rejected'"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            access_request = (
                ProjectAccessRequest.objects.select_for_update()
                .select_related("project", "requester")
                .filter(pk=pk, project_id=project_id, workspace__slug=slug)
                .first()
            )
            if access_request is None:
                return Response({"error": "Access request does not exist"}, status=status.HTTP_404_NOT_FOUND)
            if access_request.status != ProjectAccessRequest.PENDING:
                return Response({"error": "This request was already decided"}, status=status.HTTP_409_CONFLICT)

            if decision == ProjectAccessRequest.APPROVED:
                workspace_member = WorkspaceMember.objects.filter(
                    workspace__slug=slug, member_id=access_request.requester_id, is_active=True
                ).first()
                if workspace_member is None or workspace_member.role == ROLE.GUEST.value:
                    return Response(
                        {"error": "The requester is no longer a member of the workspace"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # the same role a person gets when joining a project themselves
                role = workspace_member.role
                reactivated = ProjectMember.objects.filter(
                    project_id=project_id, member_id=access_request.requester_id, is_active=False
                ).update(is_active=True, role=role, updated_by=request.user, updated_at=timezone.now())
                if reactivated:
                    ProjectUserProperty.objects.get_or_create(
                        project_id=project_id,
                        user_id=access_request.requester_id,
                        defaults={"workspace_id": access_request.project.workspace_id},
                    )
                elif not ProjectMember.objects.filter(
                    project_id=project_id, member_id=access_request.requester_id, is_active=True
                ).exists():
                    ProjectMember.objects.create(
                        project_id=project_id,
                        member_id=access_request.requester_id,
                        role=role,
                        workspace_id=access_request.project.workspace_id,
                        created_by=request.user,
                    )

            access_request.status = decision
            access_request.decided_by = request.user
            access_request.decided_at = timezone.now()
            access_request.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])

        return Response(ProjectAccessRequestSerializer(access_request).data, status=status.HTTP_200_OK)
