# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import uuid

# Django imports
from django.db import transaction

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkSpaceAdminPermission
from plane.app.serializers.initiative import InitiativeSerializer, InitiativeUpdateSerializer
from plane.db.models import (
    Initiative,
    InitiativeEpic,
    InitiativeKind,
    InitiativeProject,
    InitiativeStatus,
    InitiativeUpdate,
    Issue,
    Workspace,
)
from plane.utils.initiatives import accessible_project_ids, describe

from ..base import BaseAPIView

LINKS_ONLY_ON_INITIATIVES = "Projects and Epics are linked to initiatives, not to goals."


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _uuid_list(data, key):
    """The ids sent under ``key`` as a list of UUIDs without repeats, or None when it is not a list of ids."""
    values = data.get(key) if hasattr(data, "get") else None
    if not isinstance(values, list) or not values:
        return None
    ids = [_uuid(value) for value in values]
    return None if any(value is None for value in ids) else list(dict.fromkeys(ids))


class _InitiativeView(BaseAPIView):
    """Initiatives belong to the workspace: its admins and members read and manage them, guests have no access.

    Work item numbers come only from the projects the requester is a member of (see ``plane.utils.initiatives``).
    """

    permission_classes = [WorkSpaceAdminPermission]

    def _workspace(self, slug):
        return Workspace.objects.get(slug=slug)

    def _initiative(self, workspace, pk):
        return Initiative.objects.filter(workspace=workspace, pk=pk).first()

    def _present(self, request, workspace, initiatives):
        initiatives = list(initiatives)
        described = describe(initiatives, request.user, workspace.id)
        rows = InitiativeSerializer(initiatives, many=True).data
        return [{**row, **described[item.id]} for row, item in zip(rows, initiatives)]

    def _present_one(self, request, workspace, initiative):
        return self._present(request, workspace, [initiative])[0]


class InitiativeListEndpoint(_InitiativeView):
    def get(self, request, slug):
        workspace = self._workspace(slug)
        queryset = Initiative.objects.filter(workspace=workspace)

        kind = request.GET.get("kind")
        if kind:
            if kind not in InitiativeKind.values:
                return _error("Unknown kind.")
            queryset = queryset.filter(kind=kind)

        statuses = [value for value in request.GET.get("status", "").split(",") if value]
        if statuses:
            if any(value not in InitiativeStatus.values for value in statuses):
                return _error("Unknown status.")
            queryset = queryset.filter(status__in=statuses)

        parent = request.GET.get("parent")
        if parent:
            if parent == "none":
                queryset = queryset.filter(parent__isnull=True)
            elif _uuid(parent) is None:
                return _error("The parent must be an id or 'none'.")
            else:
                queryset = queryset.filter(parent_id=_uuid(parent))

        project = request.GET.get("project")
        if project:
            project_id = _uuid(project)
            if project_id is None:
                return _error("The project must be an id.")
            # A project the requester is not in matches nothing, or the filter would tell where it is linked
            if not accessible_project_ids(request.user, workspace.id, [project_id]):
                queryset = queryset.none()
            else:
                linked = InitiativeProject.objects.filter(workspace=workspace, project_id=project_id).values(
                    "initiative_id"
                )
                queryset = queryset.filter(pk__in=linked)

        return Response(self._present(request, workspace, queryset), status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = self._workspace(slug)
        serializer = InitiativeSerializer(data=request.data, context={"workspace_id": workspace.id})
        serializer.is_valid(raise_exception=True)
        initiative = serializer.save(workspace=workspace)
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_201_CREATED)


class InitiativeDetailEndpoint(_InitiativeView):
    def get(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)

    def patch(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        serializer = InitiativeSerializer(
            initiative, data=request.data, partial=True, context={"workspace_id": workspace.id}
        )
        serializer.is_valid(raise_exception=True)
        initiative = serializer.save()
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)

    def delete(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            # The initiatives of a deleted goal stay, without a goal
            Initiative.objects.filter(workspace=workspace, parent=initiative).update(parent=None)
            initiative.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitiativeProjectsEndpoint(_InitiativeView):
    """Link projects to an initiative. Only the projects the requester is a member of can be linked or unlinked."""

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        if initiative.kind != InitiativeKind.INITIATIVE:
            return _error(LINKS_ONLY_ON_INITIATIVES)
        project_ids = _uuid_list(request.data, "project_ids")
        if project_ids is None:
            return _error("project_ids must be a list of project ids.")
        # One answer for a project of another workspace and for one the requester is not in: neither is confirmed
        if set(project_ids) - accessible_project_ids(request.user, workspace.id, project_ids):
            return _error("Every project must be a project of this workspace that you are a member of.")

        with transaction.atomic():
            present = set(
                InitiativeProject.objects.filter(initiative=initiative, project_id__in=project_ids).values_list(
                    "project_id", flat=True
                )
            )
            for project_id in project_ids:
                if project_id not in present:
                    InitiativeProject.objects.create(initiative=initiative, project_id=project_id)
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)


class InitiativeProjectDetailEndpoint(_InitiativeView):
    def delete(self, request, slug, pk, project_id):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        link = InitiativeProject.objects.filter(initiative=initiative, project_id=project_id).first()
        if link is None or not accessible_project_ids(request.user, workspace.id, [project_id]):
            return _error("This project is not linked to the initiative.", status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitiativeEpicsEndpoint(_InitiativeView):
    """Link Epics to an initiative. Only Epics of projects the requester is a member of can be linked or unlinked."""

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        if initiative.kind != InitiativeKind.INITIATIVE:
            return _error(LINKS_ONLY_ON_INITIATIVES)
        epic_ids = _uuid_list(request.data, "epic_ids")
        if epic_ids is None:
            return _error("epic_ids must be a list of work item ids.")

        epics = list(
            Issue.issue_objects.filter(
                workspace=workspace,
                pk__in=epic_ids,
                type__is_epic=True,
                project_id__in=accessible_project_ids(request.user, workspace.id),
            ).select_related("type")
        )
        if len(epics) != len(epic_ids):
            return _error("Every work item must be an Epic in a project of this workspace that you are a member of.")

        with transaction.atomic():
            present = set(
                InitiativeEpic.objects.filter(initiative=initiative, issue_id__in=epic_ids).values_list(
                    "issue_id", flat=True
                )
            )
            for epic in epics:
                if epic.id not in present:
                    InitiativeEpic.objects.create(initiative=initiative, issue=epic)
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)


class InitiativeEpicDetailEndpoint(_InitiativeView):
    def delete(self, request, slug, pk, epic_id):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        link = InitiativeEpic.objects.filter(initiative=initiative, issue_id=epic_id).select_related("issue").first()
        if link is None or not accessible_project_ids(request.user, workspace.id, [link.issue.project_id]):
            return _error("This Epic is not linked to the initiative.", status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitiativeUpdatesEndpoint(_InitiativeView):
    """Status notes of an initiative or a goal. A new one becomes the health of the initiative."""

    def get(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        updates = InitiativeUpdate.objects.filter(initiative=initiative).select_related("author")
        return Response(InitiativeUpdateSerializer(updates, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        serializer = InitiativeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            update = serializer.save(initiative=initiative, author=request.user)
            initiative.health = update.health
            initiative.save(update_fields=["health", "updated_at", "updated_by"])
        return Response(InitiativeUpdateSerializer(update).data, status=status.HTTP_201_CREATED)
