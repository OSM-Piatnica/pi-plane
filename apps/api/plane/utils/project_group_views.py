# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
What the project groups endpoints do, shared by the app and the public API.

Both sets of views check the permissions in their own way and then call these functions, so the validation, the
messages and the effects on the project members are the same on both sides. Each function answers with a DRF
``Response``; the serializer class is passed in because each API has its own.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.db.models import Project, ProjectGroup, UserGroup, WorkspaceMember
from plane.utils.project_groups import assignable_group_ids, reconcile_project
from plane.utils.user_groups import member_user_ids

GROUP_NOT_IN_PROJECT_MESSAGE = "Group not found in the project."


def error_response(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def present_links(project, links, serializer_class):
    """Serialize project groups with the number of people who belong to the project through each."""
    links = list(links.select_related("group"))
    active = set(
        WorkspaceMember.objects.filter(workspace_id=project.workspace_id, is_active=True).values_list(
            "member_id", flat=True
        )
    )
    for link in links:
        link.member_count = len(member_user_ids(project.workspace_id, [link.group_id]) & active)
    return serializer_class(links, many=True).data


def wants_assignable(request):
    return str(request.query_params.get("assignable", "")).lower() in {"1", "true"}


def list_groups(request, project, serializer_class):
    """The groups of the project, or with ``?assignable=1`` the groups its work items can be assigned to."""
    if wants_assignable(request):
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
    return Response(present_links(project, links, serializer_class), status=status.HTTP_200_OK)


def add_group(data, project, serializer_class):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    group = serializer.validated_data["group"]
    if group.workspace_id != project.workspace_id:
        return error_response("The group does not exist in this workspace.")
    if ProjectGroup.objects.filter(project=project, group=group).exists():
        return error_response("This group is already a member of the project.", status.HTTP_409_CONFLICT)
    link = serializer.save(project=project, workspace=project.workspace)
    reconcile_project(project.id)
    return Response(
        present_links(project, ProjectGroup.objects.filter(pk=link.pk), serializer_class)[0],
        status=status.HTTP_201_CREATED,
    )


def find_link(slug, project_id, pk):
    return ProjectGroup.objects.filter(
        pk=pk, project_id=project_id, workspace__slug=slug, group__deleted_at__isnull=True
    ).first()


def change_group_role(data, slug, project_id, pk, serializer_class):
    link = find_link(slug, project_id, pk)
    if link is None:
        return error_response(GROUP_NOT_IN_PROJECT_MESSAGE, status.HTTP_404_NOT_FOUND)
    # Only the role can change; moving the link to another group is removing and adding
    serializer = serializer_class(link, data={"role": data.get("role")}, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    reconcile_project(link.project_id)
    project = Project.objects.get(pk=project_id)
    return Response(
        present_links(project, ProjectGroup.objects.filter(pk=link.pk), serializer_class)[0],
        status=status.HTTP_200_OK,
    )


def remove_group(slug, project_id, pk):
    link = find_link(slug, project_id, pk)
    if link is None:
        return error_response(GROUP_NOT_IN_PROJECT_MESSAGE, status.HTTP_404_NOT_FOUND)
    link.delete()
    reconcile_project(link.project_id)
    return Response(status=status.HTTP_204_NO_CONTENT)
