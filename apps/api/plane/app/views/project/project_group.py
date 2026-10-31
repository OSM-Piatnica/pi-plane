# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Module imports
from .base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.project_group import ProjectGroupSerializer
from plane.db.models import Project
from plane.utils.project_group_views import add_group, change_group_role, list_groups, remove_group


class ProjectGroupEndpoint(BaseAPIView):
    """The groups that are members of a project: anyone in the project reads, project admins change."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        return list_groups(request, project, ProjectGroupSerializer)

    @allow_permission([ROLE.ADMIN])
    def post(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        return add_group(request.data, project, ProjectGroupSerializer)


class ProjectGroupDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN])
    def patch(self, request, slug, project_id, pk):
        return change_group_role(request.data, slug, project_id, pk, ProjectGroupSerializer)

    @allow_permission([ROLE.ADMIN])
    def delete(self, request, slug, project_id, pk):
        return remove_group(slug, project_id, pk)
