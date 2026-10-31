# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiRequest, OpenApiResponse, extend_schema

# Module imports
from .base import BaseAPIView
from plane.api.serializers import (
    ProjectGroupRoleUpdateSerializer,
    ProjectGroupSerializer,
)
from plane.db.models import Project
from plane.utils.openapi import (
    FORBIDDEN_RESPONSE,
    INVALID_REQUEST_RESPONSE,
    PROJECT_ID_PARAMETER,
    PROJECT_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    WORKSPACE_SLUG_PARAMETER,
)
from plane.utils.permissions import ProjectAdminPermission, ProjectMemberPermission
from plane.utils.project_group_views import add_group, change_group_role, list_groups, remove_group

GROUP_LINK_ID_PARAMETER = OpenApiParameter(
    name="pk",
    description="ID of the project group (the link between the project and the group, not the group's own ID)",
    required=True,
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
)
ASSIGNABLE_PARAMETER = OpenApiParameter(
    name="assignable",
    description=(
        "Pass 1 to list the groups work items of the project can be assigned to (the groups of the project and "
        "the groups below them) instead of the groups of the project."
    ),
    required=False,
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
)
GROUP_NOT_FOUND_RESPONSE = OpenApiResponse(description="Group not found in the project")
GROUP_CONFLICT_RESPONSE = OpenApiResponse(description="The group is already a member of the project")


class ProjectGroupListCreateAPIEndpoint(BaseAPIView):
    """The groups that are members of a project: anyone in the project reads, project admins change."""

    permission_classes = [ProjectMemberPermission]
    use_read_replica = True

    def get_permissions(self):
        if self.request.method == "GET":
            return [ProjectMemberPermission()]
        return [ProjectAdminPermission()]

    @extend_schema(
        operation_id="get_project_groups",
        summary="List project groups",
        description="Retrieve the user groups that are members of the project, with the role each gives its people.",
        tags=["Project Groups"],
        parameters=[WORKSPACE_SLUG_PARAMETER, PROJECT_ID_PARAMETER, ASSIGNABLE_PARAMETER],
        responses={
            200: OpenApiResponse(
                description="Groups of the project (or, with assignable=1, the groups work items can be assigned to)",
                response=ProjectGroupSerializer(many=True),
            ),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: PROJECT_NOT_FOUND_RESPONSE,
        },
    )
    def get(self, request, slug, project_id):
        """List project groups

        Retrieve the groups of the project. With `assignable=1` the answer lists the groups work items of the
        project can be assigned to instead: the groups of the project and the groups below them.
        """
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        return list_groups(request, project, ProjectGroupSerializer)

    @extend_schema(
        operation_id="create_project_group",
        summary="Add a group to a project",
        description=(
            "Make a user group a member of the project as a Member (15) or a Guest (5). Its people, and the "
            "people of the groups below it, become project members. Project admins only."
        ),
        tags=["Project Groups"],
        parameters=[WORKSPACE_SLUG_PARAMETER, PROJECT_ID_PARAMETER],
        request=OpenApiRequest(request=ProjectGroupSerializer),
        responses={
            201: OpenApiResponse(description="Group added to the project", response=ProjectGroupSerializer),
            400: INVALID_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: PROJECT_NOT_FOUND_RESPONSE,
            409: GROUP_CONFLICT_RESPONSE,
        },
    )
    def post(self, request, slug, project_id):
        """Add a group to a project

        Make a user group a member of the project with the role Member (15) or Guest (5).
        """
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        return add_group(request.data, project, ProjectGroupSerializer)


class ProjectGroupDetailAPIEndpoint(BaseAPIView):
    """Change the role of a group of a project, or take the group out of it (project admins only)."""

    permission_classes = [ProjectAdminPermission]

    @extend_schema(
        operation_id="update_project_group",
        summary="Change the role of a project group",
        description="Change the role (Member 15 or Guest 5) a group of the project gives its people.",
        tags=["Project Groups"],
        parameters=[WORKSPACE_SLUG_PARAMETER, PROJECT_ID_PARAMETER, GROUP_LINK_ID_PARAMETER],
        request=OpenApiRequest(request=ProjectGroupRoleUpdateSerializer),
        responses={
            200: OpenApiResponse(description="Project group updated", response=ProjectGroupSerializer),
            400: INVALID_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: GROUP_NOT_FOUND_RESPONSE,
        },
    )
    def patch(self, request, slug, project_id, pk):
        """Change the role of a project group"""
        return change_group_role(request.data, slug, project_id, pk, ProjectGroupSerializer)

    @extend_schema(
        operation_id="delete_project_group",
        summary="Remove a group from a project",
        description="Take a group out of the project. People who belong to the project only through it leave too.",
        tags=["Project Groups"],
        parameters=[WORKSPACE_SLUG_PARAMETER, PROJECT_ID_PARAMETER, GROUP_LINK_ID_PARAMETER],
        responses={
            204: OpenApiResponse(description="Group removed from the project"),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: GROUP_NOT_FOUND_RESPONSE,
        },
    )
    def delete(self, request, slug, project_id, pk):
        """Remove a group from a project"""
        return remove_group(slug, project_id, pk)
