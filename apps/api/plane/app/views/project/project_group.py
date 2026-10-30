# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.project_group import ProjectGroupSerializer
from plane.db.models import Project, ProjectGroup, UserGroup, WorkspaceMember
from plane.utils.project_groups import assignable_group_ids, reconcile_project
from plane.utils.user_groups import member_user_ids


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _present(project, links):
    """Serialize project groups with the number of people who belong to the project through each."""
    links = list(links.select_related("group"))
    active = set(
        WorkspaceMember.objects.filter(workspace_id=project.workspace_id, is_active=True).values_list(
            "member_id", flat=True
        )
    )
    for link in links:
        link.member_count = len(member_user_ids(project.workspace_id, [link.group_id]) & active)
    return ProjectGroupSerializer(links, many=True).data


class ProjectGroupEndpoint(BaseAPIView):
    """The groups that are members of a project: anyone in the project reads, project admins change."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        if str(request.query_params.get("assignable", "")).lower() in {"1", "true"}:
            ids = assignable_group_ids(project.id, project.workspace_id)
            groups = UserGroup.objects.filter(workspace_id=project.workspace_id, id__in=ids).order_by("name")
            return Response(
                [
                    {"id": group.id, "name": group.name, "source": group.source, "parent_id": group.parent_id}
                    for group in groups
                ],
                status=status.HTTP_200_OK,
            )
        links = ProjectGroup.objects.filter(project=project, group__deleted_at__isnull=True).order_by("group__name")
        return Response(_present(project, links), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def post(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        serializer = ProjectGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.validated_data["group"]
        if group.workspace_id != project.workspace_id:
            return _error("The group does not exist in this workspace.")
        if ProjectGroup.objects.filter(project=project, group=group).exists():
            return _error("This group is already a member of the project.", status.HTTP_409_CONFLICT)
        link = serializer.save(project=project, workspace=project.workspace)
        reconcile_project(project.id)
        return Response(
            _present(project, ProjectGroup.objects.filter(pk=link.pk))[0],
            status=status.HTTP_201_CREATED,
        )


class ProjectGroupDetailEndpoint(BaseAPIView):
    def _link(self, slug, project_id, pk):
        return ProjectGroup.objects.filter(
            pk=pk, project_id=project_id, workspace__slug=slug, group__deleted_at__isnull=True
        ).first()

    @allow_permission([ROLE.ADMIN])
    def patch(self, request, slug, project_id, pk):
        link = self._link(slug, project_id, pk)
        if link is None:
            return _error("Group not found in the project.", status.HTTP_404_NOT_FOUND)
        # Only the role can change; moving the link to another group is removing and adding
        serializer = ProjectGroupSerializer(link, data={"role": request.data.get("role")}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        reconcile_project(link.project_id)
        project = Project.objects.get(pk=project_id)
        return Response(_present(project, ProjectGroup.objects.filter(pk=link.pk))[0], status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def delete(self, request, slug, project_id, pk):
        link = self._link(slug, project_id, pk)
        if link is None:
            return _error("Group not found in the project.", status.HTTP_404_NOT_FOUND)
        link.delete()
        reconcile_project(link.project_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
