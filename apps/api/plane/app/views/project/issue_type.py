# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import IssueTypeSerializer, ProjectIssueTypeSerializer
from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.db.models import SYSTEM_MANAGED_ISSUE_TYPE_KINDS, IssueType, IssueTypeKind, Project, ProjectIssueType
from plane.utils.project_issue_types import (
    EpicsNotAvailableError,
    ensure_project_epic_type,
    remove_project_epic_types,
)


class ProjectIssueTypeViewSet(BaseViewSet):
    serializer_class = ProjectIssueTypeSerializer
    model = ProjectIssueType
    use_read_replica = True

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                project_id=self.kwargs.get("project_id"),
                workspace__slug=self.kwargs.get("slug"),
                issue_type__is_active=True,
                issue_type__deleted_at__isnull=True,
            )
            .select_related("issue_type", "project", "workspace")
            .order_by("level", "issue_type__name")
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def list(self, request, slug, project_id):
        qs = self.filter_queryset(self.get_queryset())
        return self.paginate(
            request=request,
            queryset=qs,
            on_results=lambda rows: ProjectIssueTypeSerializer(rows, many=True).data,
            default_per_page=100,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def create(self, request, slug, project_id):
        issue_type_id = request.data.get("issue_type_id")
        if not issue_type_id:
            return Response({"error": "issue_type_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            parsed_type_id = uuid.UUID(str(issue_type_id))
        except (ValueError, TypeError, AttributeError):
            return Response({"error": "Invalid issue_type_id"}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.filter(id=project_id, workspace__slug=slug, deleted_at__isnull=True).first()
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        issue_type = IssueType.objects.filter(
            id=parsed_type_id,
            workspace_id=project.workspace_id,
            deleted_at__isnull=True,
        ).first()
        if not issue_type:
            return Response({"error": "Issue type not found"}, status=status.HTTP_404_NOT_FOUND)

        existing = ProjectIssueType.objects.filter(
            project_id=project_id,
            issue_type_id=parsed_type_id,
            deleted_at__isnull=True,
        ).first()
        if existing:
            return Response(ProjectIssueTypeSerializer(existing).data, status=status.HTTP_200_OK)

        is_default = bool(request.data.get("is_default", False))
        level = request.data.get("level")
        try:
            level = int(level) if level is not None else issue_type.level
        except (TypeError, ValueError):
            level = issue_type.level

        with transaction.atomic():
            if is_default:
                ProjectIssueType.objects.filter(project_id=project_id, deleted_at__isnull=True).update(is_default=False)
            link = ProjectIssueType.objects.create(
                project_id=project_id,
                issue_type_id=parsed_type_id,
                workspace_id=project.workspace_id,
                level=level,
                is_default=is_default,
            )

        return Response(ProjectIssueTypeSerializer(link).data, status=status.HTTP_201_CREATED)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def partial_update(self, request, slug, project_id, pk):
        link = self.get_queryset().filter(pk=pk).first()
        if not link:
            return Response({"error": "Project issue type not found"}, status=status.HTTP_404_NOT_FOUND)

        is_default = request.data.get("is_default")
        level = request.data.get("level")

        with transaction.atomic():
            if is_default is True:
                ProjectIssueType.objects.filter(project_id=project_id, deleted_at__isnull=True).exclude(pk=pk).update(
                    is_default=False
                )
                link.is_default = True
            if level is not None:
                try:
                    link.level = int(level)
                except (TypeError, ValueError):
                    pass
            link.save()

        return Response(ProjectIssueTypeSerializer(link).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def destroy(self, request, slug, project_id, pk):
        return super().destroy(request, slug, project_id, pk)


# Kinds whose links a type list never removes: Epic types belong to the Epics switch, system-managed types
# (approval, review) to the feature that links them through `ensure_project_kind_type`
KINDS_KEPT_BY_BULK_ASSIGN = frozenset({IssueTypeKind.EPIC, *SYSTEM_MANAGED_ISSUE_TYPE_KINDS})


class ProjectIssueTypeBulkAssignEndpoint(BaseAPIView):
    """Set the types a project can use from a list. A list neither adds nor removes a system-managed type."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def post(self, request, slug, project_id):
        issue_type_ids = request.data.get("issue_type_ids")
        if not isinstance(issue_type_ids, list):
            return Response({"error": "issue_type_ids must be an array"}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.filter(id=project_id, workspace__slug=slug, deleted_at__isnull=True).first()
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        parsed_ids = []
        for raw in issue_type_ids:
            try:
                parsed_ids.append(uuid.UUID(str(raw)))
            except (ValueError, TypeError, AttributeError):
                continue

        valid_types = list(
            IssueType.objects.filter(
                workspace_id=project.workspace_id,
                id__in=parsed_ids,
                deleted_at__isnull=True,
                is_active=True,
            ).exclude(kind__in=SYSTEM_MANAGED_ISSUE_TYPE_KINDS)
        )

        default_type_id = request.data.get("default_type_id")
        default_uuid = None
        if default_type_id:
            try:
                default_uuid = uuid.UUID(str(default_type_id))
            except (ValueError, TypeError, AttributeError):
                default_uuid = None

        with transaction.atomic():
            existing = {
                str(row.issue_type_id): row
                for row in ProjectIssueType.objects.filter(
                    project_id=project_id, deleted_at__isnull=True
                ).select_related("issue_type")
            }
            # The default must be one of the types this list links. A system-managed type (left out of
            # `valid_types`) is never the type a new work item starts with, and a default that is not linked
            # would leave the project without one; either way the current default stays.
            if default_uuid not in {issue_type.id for issue_type in valid_types}:
                default_uuid = None
            keep = set()
            for issue_type in valid_types:
                keep.add(str(issue_type.id))
                if str(issue_type.id) not in existing:
                    ProjectIssueType.objects.create(
                        project_id=project_id,
                        issue_type=issue_type,
                        workspace_id=project.workspace_id,
                        level=issue_type.level,
                        is_default=default_uuid == issue_type.id,
                    )
                elif default_uuid == issue_type.id:
                    existing[str(issue_type.id)].is_default = True
                    existing[str(issue_type.id)].save()
            for key, row in existing.items():
                # Epics are switched on and off through the Epics endpoint only, so a list that leaves an Epic
                # type out (the settings list does not show them) never turns Epics off; the same holds for the
                # system-managed types, which the lists do not show either
                if key not in keep and row.issue_type.kind not in KINDS_KEPT_BY_BULK_ASSIGN:
                    row.delete()

            if default_uuid:
                ProjectIssueType.objects.filter(project_id=project_id, deleted_at__isnull=True).update(is_default=False)
                ProjectIssueType.objects.filter(
                    project_id=project_id,
                    issue_type_id=default_uuid,
                    deleted_at__isnull=True,
                ).update(is_default=True)

        rows = self._get_links(project_id)
        return Response(
            {"results": [IssueTypeSerializer(row.issue_type, context={"slug": slug}).data for row in rows]},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_links(project_id):
        return ProjectIssueType.objects.filter(
            project_id=project_id,
            deleted_at__isnull=True,
            issue_type__deleted_at__isnull=True,
            issue_type__is_active=True,
        ).select_related("issue_type")


class ProjectEpicsEndpoint(BaseAPIView):
    """The per-project Epics switch: on links the workspace's Epic type, off unlinks the Epic types."""

    def _project(self, slug, project_id):
        return Project.objects.filter(id=project_id, workspace__slug=slug, deleted_at__isnull=True).first()

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def post(self, request, slug, project_id):
        project = self._project(slug, project_id)
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                epic_type = ensure_project_epic_type(project, created_by_id=request.user.id)
        except EpicsNotAvailableError:
            # A fixed message: nothing of the exception itself goes into the response
            return Response(
                {"error": "Work item types are not enabled for this project"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(IssueTypeSerializer(epic_type, context={"slug": slug}).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def delete(self, request, slug, project_id):
        project = self._project(slug, project_id)
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        remove_project_epic_types(project)
        return Response(status=status.HTTP_204_NO_CONTENT)
