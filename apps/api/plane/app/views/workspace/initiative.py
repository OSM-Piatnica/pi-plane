# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import uuid

# Django imports
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q

# Third party imports
from rest_framework import status
from rest_framework.permissions import BasePermission
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
    Project,
    Workspace,
)
from plane.utils.user_groups import is_workspace_admin
from plane.utils.initiatives import accessible_project_ids, describe, linked_epics, project_access
from plane.utils.workspace_features import is_workspace_feature_enabled

from ..base import BaseAPIView

LINKS_ONLY_ON_INITIATIVES = "Projects and Epics are linked to initiatives, not to goals."
# The most projects or Epics one request may link
MAX_LINKS_PER_REQUEST = 100
NOT_ALLOWED_TO_UNLINK = "Only a member of the project (not a guest) or a workspace admin can unlink it."
NOT_ALLOWED_TO_LINK = "Only a member of the project (not a guest) or a workspace admin can link it or its Epics."
# The most Epics one search returns
MAX_EPIC_SEARCH_RESULTS = 20


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _uuid_list(data, key):
    """The ids sent under ``key`` as a list of UUIDs without repeats.

    None when it is not a list of ids, is empty or has more than ``MAX_LINKS_PER_REQUEST`` entries.
    """
    values = data.get(key) if hasattr(data, "get") else None
    if not isinstance(values, list) or not values or len(values) > MAX_LINKS_PER_REQUEST:
        return None
    ids = [_uuid(value) for value in values]
    return None if any(value is None for value in ids) else list(dict.fromkeys(ids))


class InitiativesSwitchedOn(BasePermission):
    """The Initiatives feature is switched on for the workspace (``WorkspaceFeature``, key ``initiatives``)."""

    message = "Initiatives are switched off in this workspace."

    def has_permission(self, request, view):
        workspace = Workspace.objects.filter(slug=view.workspace_slug).first()
        return workspace is not None and is_workspace_feature_enabled(workspace, "initiatives")


class _InitiativeView(BaseAPIView):
    """Initiatives belong to the workspace: its admins and members read and manage them, guests have no access.

    They answer only while a workspace admin has switched the feature on (``docs/workspace-features.md``).
    Work item numbers come only from the projects the requester may see: all of them for a workspace admin, their
    own for a member (see ``plane.utils.initiatives``).
    """

    permission_classes = [WorkSpaceAdminPermission, InitiativesSwitchedOn]

    def handle_exception(self, exc):
        # What a model refuses is said in its own words; the base view would answer with a general message
        if isinstance(exc, DjangoValidationError):
            if hasattr(exc, "message_dict"):
                return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
            return _error(" ".join(exc.messages))
        return super().handle_exception(exc)

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
        # Editing is open to every member; deleting is for a workspace admin, the lead and the person who made it
        if request.user.id not in (initiative.lead_id, initiative.created_by_id) and not is_workspace_admin(
            request.user, workspace.id
        ):
            return _error("Only a workspace admin, the lead or the creator can delete this.", status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            # The initiatives of a deleted goal stay, without a goal
            Initiative.objects.filter(workspace=workspace, parent=initiative).update(parent=None)
            initiative.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitiativeProjectsEndpoint(_InitiativeView):
    """Link projects to an initiative.

    Linking and unlinking takes at least the Member role in the project, or a workspace admin (``project_access``).
    """

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        if initiative.kind != InitiativeKind.INITIATIVE:
            return _error(LINKS_ONLY_ON_INITIATIVES)
        project_ids = _uuid_list(request.data, "project_ids")
        if project_ids is None:
            return _error(f"project_ids must be a list of 1 to {MAX_LINKS_PER_REQUEST} project ids.")
        # One answer for a project of another workspace and for one the requester cannot see: neither is confirmed
        viewable, manageable = project_access(request.user, workspace.id, project_ids)
        if set(project_ids) - viewable:
            return _error("Every project must be a project of this workspace that you can see.")
        if set(project_ids) - manageable:
            return _error(NOT_ALLOWED_TO_LINK, status.HTTP_403_FORBIDDEN)
        if Project.objects.filter(pk__in=project_ids, archived_at__isnull=False).exists():
            return _error("An archived project cannot be linked.")

        present = set(
            InitiativeProject.objects.filter(initiative=initiative, project_id__in=project_ids).values_list(
                "project_id", flat=True
            )
        )
        # Checked above, so the rows are written in one statement without the per-row checks of save()
        InitiativeProject.objects.bulk_create(
            [
                InitiativeProject(
                    workspace_id=workspace.id,
                    initiative=initiative,
                    project_id=project_id,
                    created_by=request.user,
                )
                for project_id in project_ids
                if project_id not in present
            ],
            ignore_conflicts=True,
        )
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)


class InitiativeProjectDetailEndpoint(_InitiativeView):
    def delete(self, request, slug, pk, project_id):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        link = InitiativeProject.objects.filter(initiative=initiative, project_id=project_id).first()
        viewable, manageable = project_access(request.user, workspace.id, [project_id])
        if link is None or project_id not in viewable:
            return _error("This project is not linked to the initiative.", status.HTTP_404_NOT_FOUND)
        if project_id not in manageable:
            return _error(NOT_ALLOWED_TO_UNLINK, status.HTTP_403_FORBIDDEN)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitiativeEpicsEndpoint(_InitiativeView):
    """The linked Epics, and linking Epics to an initiative.

    Linking and unlinking takes at least the Member role in the project of the Epic, or a workspace admin.
    """

    def get(self, request, slug, pk):
        """The linked Epics the requester may see, each with the progress of its child work items.

        For a goal, the Epics of its initiatives, each once. Hidden Epics are only counted, in the initiative's
        ``hidden_epic_count``.
        """
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        return Response(linked_epics(initiative, request.user, workspace.id), status=status.HTTP_200_OK)

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        if initiative.kind != InitiativeKind.INITIATIVE:
            return _error(LINKS_ONLY_ON_INITIATIVES)
        epic_ids = _uuid_list(request.data, "epic_ids")
        if epic_ids is None:
            return _error(f"epic_ids must be a list of 1 to {MAX_LINKS_PER_REQUEST} work item ids.")

        viewable, manageable = project_access(request.user, workspace.id)
        found = list(
            Issue.issue_objects.filter(
                workspace=workspace, pk__in=epic_ids, type__is_epic=True, project_id__in=viewable
            ).values_list("id", "project_id")
        )
        if len(found) != len(epic_ids):
            return _error(
                "Every work item must be an Epic that is not archived, in a project of this workspace that you can see."
            )
        if any(project_id not in manageable for _, project_id in found):
            return _error(NOT_ALLOWED_TO_LINK, status.HTTP_403_FORBIDDEN)
        # In the order of the request: the links are listed in the order they were made
        found_ids = {epic_id for epic_id, _ in found}
        epics = [epic_id for epic_id in epic_ids if epic_id in found_ids]

        present = set(
            InitiativeEpic.objects.filter(initiative=initiative, issue_id__in=epic_ids).values_list(
                "issue_id", flat=True
            )
        )
        # Checked above, so the rows are written in one statement without the per-row checks of save()
        InitiativeEpic.objects.bulk_create(
            [
                InitiativeEpic(
                    workspace_id=workspace.id, initiative=initiative, issue_id=epic_id, created_by=request.user
                )
                for epic_id in epics
                if epic_id not in present
            ],
            ignore_conflicts=True,
        )
        return Response(self._present_one(request, workspace, initiative), status=status.HTTP_200_OK)


class InitiativeEpicSearchEndpoint(_InitiativeView):
    """Epics the requester may link to an initiative: in a project they may link, not archived, not linked yet."""

    def get(self, request, slug, pk):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        if initiative.kind != InitiativeKind.INITIATIVE:
            return _error(LINKS_ONLY_ON_INITIATIVES)
        _, manageable = project_access(request.user, workspace.id)
        epics = Issue.issue_objects.filter(workspace=workspace, type__is_epic=True, project_id__in=manageable).exclude(
            pk__in=InitiativeEpic.objects.filter(initiative=initiative).values("issue_id"),
        )
        search = request.GET.get("search", "").strip()
        if search:
            match = Q(name__icontains=search)
            # "12" or "ABC-12": the number of the Epic, with or without the identifier of its project
            identifier, _, number = search.rpartition("-")
            if number.isdigit():
                by_number = Q(sequence_id=int(number))
                if identifier:
                    by_number &= Q(project__identifier__iexact=identifier)
                match |= by_number
            epics = epics.filter(match)
        rows = epics.order_by("-updated_at").values("id", "name", "sequence_id", "project_id", "project__identifier")[
            :MAX_EPIC_SEARCH_RESULTS
        ]
        return Response(
            [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "sequence_id": row["sequence_id"],
                    "project_id": row["project_id"],
                    "project_identifier": row["project__identifier"],
                }
                for row in rows
            ],
            status=status.HTTP_200_OK,
        )


class InitiativeEpicDetailEndpoint(_InitiativeView):
    def delete(self, request, slug, pk, epic_id):
        workspace = self._workspace(slug)
        initiative = self._initiative(workspace, pk)
        if initiative is None:
            return _error("Initiative not found.", status.HTTP_404_NOT_FOUND)
        link = InitiativeEpic.objects.filter(initiative=initiative, issue_id=epic_id).select_related("issue").first()
        if link is None:
            return _error("This Epic is not linked to the initiative.", status.HTTP_404_NOT_FOUND)
        project_id = link.issue.project_id
        viewable, manageable = project_access(request.user, workspace.id, [project_id])
        if project_id not in viewable:
            return _error("This Epic is not linked to the initiative.", status.HTTP_404_NOT_FOUND)
        if project_id not in manageable:
            return _error(NOT_ALLOWED_TO_UNLINK, status.HTTP_403_FORBIDDEN)
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
