# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import IntegrityError

# Third party imports
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.license.api.permissions import InstanceAdminPermission
from plane.license.api.serializers import InstanceThemeSerializer
from plane.license.models import InstanceTheme
from plane.license.utils.instance_theme import clean_theme_data


class InstanceThemeEndpoint(BaseAPIView):
    """Every signed-in user lists the themes; only instance admins change them."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [InstanceAdminPermission()]

    def get(self, request):
        themes = InstanceTheme.objects.all()
        return Response(InstanceThemeSerializer(themes, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        cleaned, errors = clean_theme_data(request.data)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        if InstanceTheme.objects.filter(name__iexact=cleaned["name"]).exists():
            return Response({"name": "A theme with this name already exists."}, status=status.HTTP_409_CONFLICT)
        theme = InstanceTheme.objects.create(source=InstanceTheme.Source.ADMIN, **cleaned)
        return Response(InstanceThemeSerializer(theme).data, status=status.HTTP_201_CREATED)


class InstanceThemeDetailEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def _get_editable(self, pk):
        theme = InstanceTheme.objects.filter(pk=pk).first()
        if theme is None:
            return None, Response({"error": "Theme not found."}, status=status.HTTP_404_NOT_FOUND)
        if theme.source == InstanceTheme.Source.DEPLOYMENT:
            return None, Response(
                {"error": "This theme comes from the deployment and cannot be changed here."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return theme, None

    def patch(self, request, pk):
        theme, error = self._get_editable(pk)
        if error:
            return error
        current = {
            "name": theme.name,
            "primary": theme.primary,
            "background": theme.background,
            "dark_palette": theme.dark_palette,
            "overrides": theme.overrides,
        }
        cleaned, errors = clean_theme_data({**current, **request.data})
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        if InstanceTheme.objects.filter(name__iexact=cleaned["name"]).exclude(pk=theme.pk).exists():
            return Response({"name": "A theme with this name already exists."}, status=status.HTTP_409_CONFLICT)
        for field, value in cleaned.items():
            setattr(theme, field, value)
        try:
            theme.save()
        except IntegrityError:
            return Response({"name": "A theme with this name already exists."}, status=status.HTTP_409_CONFLICT)
        return Response(InstanceThemeSerializer(theme).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        theme, error = self._get_editable(pk)
        if error:
            return error
        # a real delete: the name is unique, and a soft-deleted theme would keep it taken
        theme.delete(soft=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
