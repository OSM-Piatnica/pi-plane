# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.views.base import BaseAPIView
from plane.license.api.serializers import InstanceThemeSerializer
from plane.license.models import InstanceTheme


class UserInstanceThemeEndpoint(BaseAPIView):
    """The themes the instance added, for the theme list of any signed-in person.

    The same list is served to instance admins at /api/instances/themes/, but every path with "instances" in it is
    authenticated by the God Mode session only, so people using the web app need this one.
    """

    def get(self, request):
        themes = InstanceTheme.objects.all()
        return Response(InstanceThemeSerializer(themes, many=True).data, status=status.HTTP_200_OK)
