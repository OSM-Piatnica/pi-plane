# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import re

# Django imports
from django.http import HttpResponse
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

# Module imports
from .base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Project
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.serializers.project_member import ProjectMemberExportSerializer
from plane.utils.project_member_export import project_member_export_rows

CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ProjectMemberExportUserThrottle(SimpleRateThrottle):
    scope = "project_member_export_user"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class ProjectMemberExportEndpoint(BaseAPIView):
    """Download the members of a project as CSV, Excel or JSON. Project admins only, like the import."""

    throttle_classes = [ProjectMemberExportUserThrottle]

    def perform_content_negotiation(self, request, force=False):
        # `?format=` names the file format here; DRF would read it as a renderer suffix and answer 404
        renderer = self.get_renderers()[0]
        return renderer, renderer.media_type

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def get(self, request, slug, project_id):
        file_format = request.query_params.get("format", "csv").lower()
        if file_format not in CONTENT_TYPES:
            return Response({"error": "format must be csv, xlsx or json."}, status=status.HTTP_400_BAD_REQUEST)
        include_via_group = request.query_params.get("include_via_group", "0").lower() in ("1", "true")
        delimiter = request.query_params.get("delimiter", ",")

        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        rows = project_member_export_rows(project, include_via_group=include_via_group)
        identifier = re.sub(r"[^A-Za-z0-9_-]", "", project.identifier or "") or "project"
        exporter = DataExporter(ProjectMemberExportSerializer, format_type=file_format, csv_delimiter=delimiter)
        filename, content = exporter.export(f"{identifier}-members-{timezone.now().date().isoformat()}", rows)

        response = HttpResponse(content, content_type=CONTENT_TYPES[file_format])
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response
