# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.bgtasks.project_add_user_email_task import project_add_user_email
from plane.db.models import Project, ProjectMember
from plane.utils.host import base_host
from plane.utils.project_member_import import MAX_ROWS, import_project_members


class ProjectMemberImportEndpoint(BaseAPIView):
    """Add people and groups to a project from CSV rows. Project admins only, like the member and group endpoints."""

    @allow_permission([ROLE.ADMIN])
    def post(self, request, slug, project_id):
        rows = request.data.get("rows")
        if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
            return Response({"error": "At least one row is required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(rows) > MAX_ROWS:
            return Response(
                {"error": f"At most {MAX_ROWS} rows can be imported at once."}, status=status.HTTP_400_BAD_REQUEST
            )
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        summary, user_ids = import_project_members(project, rows)
        for member_id in ProjectMember.objects.filter(project_id=project.id, member_id__in=user_ids).values_list(
            "id", flat=True
        ):
            project_add_user_email.delay(base_host(request=request, is_app=True), member_id, request.user.id)
        return Response(summary, status=status.HTTP_200_OK)
