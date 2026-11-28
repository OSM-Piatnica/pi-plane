# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import IssueTypeSerializer
from plane.app.views.base import BaseAPIView
from plane.db.models import Workspace
from plane.utils.issue_type_catalogue import CATALOGUE_KEYS, add_catalogue_types, list_catalogue


class WorkspaceIssueTypeCatalogueEndpoint(BaseAPIView):
    """The catalogue of ready-made work item types (`plane.utils.issue_type_catalogue`).

    GET lists the entries in `?language=` (English when the catalogue has no text in it) with the id of the
    workspace's type that already stands for each. POST `{"keys": [...], "language": "pl"}` adds the entries.
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(list_catalogue(workspace.id, request.query_params.get("language")), status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace not found"}, status=status.HTTP_404_NOT_FOUND)
        keys = request.data.get("keys")
        if (
            not isinstance(keys, list)
            or not keys
            or not all(isinstance(key, str) and key in CATALOGUE_KEYS for key in keys)
        ):
            # A fixed message: the request's own values are not echoed back
            return Response(
                {"error": "keys must be a non-empty list of catalogue entries", "allowed": list(CATALOGUE_KEYS)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results = add_catalogue_types(
            workspace.id, keys, language=request.data.get("language"), created_by_id=request.user.id
        )
        context = {"slug": slug}
        return Response(
            [
                {"key": key, "status": result, "issue_type": IssueTypeSerializer(issue_type, context=context).data}
                for key, issue_type, result in results
            ],
            status=status.HTTP_200_OK,
        )
