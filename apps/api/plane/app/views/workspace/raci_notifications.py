# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The RACI notification matrix of a workspace: which roles hear about which events on a work item."""

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Workspace
from plane.utils.raci_notifications import (
    DEFAULT_MATRIX,
    EVENTS,
    RaciMatrixError,
    clean_matrix,
    normalize_matrix,
    save_workspace_matrix,
    workspace_matrix,
)

from ..base import BaseAPIView


def _answer(matrix):
    return {"events": list(EVENTS), "matrix": matrix, "defaults": normalize_matrix(DEFAULT_MATRIX)}


class WorkspaceRaciNotificationsEndpoint(BaseAPIView):
    """
    GET (any member) answers ``{"events": [...], "matrix": {event: [roles]}, "defaults": {...}}``.

    PATCH (workspace admins) takes ``{"matrix": {event: [roles]}}`` with some or all events and answers the same as
    GET. An event left out keeps what it has; an empty list tells nobody by role about it.
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        return Response(_answer(workspace_matrix(workspace.id)), status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def patch(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        data = request.data.get("matrix") if isinstance(request.data, dict) else None
        try:
            changes = clean_matrix(data)
        except RaciMatrixError as exc:
            return Response({"error": exc.public_message}, status=status.HTTP_400_BAD_REQUEST)
        matrix = save_workspace_matrix(workspace.id, changes, actor=request.user)
        return Response(_answer(matrix), status=status.HTTP_200_OK)
