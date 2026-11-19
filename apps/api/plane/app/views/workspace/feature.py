# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Workspace, WorkspaceFeature
from plane.utils.workspace_features import (
    is_available_workspace_feature,
    is_known_workspace_feature,
    workspace_feature_states,
)

from ..base import BaseAPIView


class WorkspaceFeatureEndpoint(BaseAPIView):
    """The feature switches of a workspace: ``{key: is_enabled}`` for every available feature.

    Every member reads them, guests included: the navigation depends on them. Only workspace admins change them.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        return Response(workspace_feature_states(workspace), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def patch(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)

        data = request.data
        if not isinstance(data, dict) or not data:
            return Response(
                {"error": "Send an object of feature keys and true or false"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # validate everything first: nothing is saved when one entry is wrong
        errors = {}
        for key, value in data.items():
            if not is_known_workspace_feature(key):
                errors[key] = "Unknown feature"
            elif not is_available_workspace_feature(key):
                errors[key] = "This feature is not available"
            elif not isinstance(value, bool):
                errors[key] = "Must be true or false"
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        for key, value in data.items():
            WorkspaceFeature.objects.update_or_create(workspace=workspace, key=key, defaults={"is_enabled": value})

        return Response(workspace_feature_states(workspace), status=status.HTTP_200_OK)
