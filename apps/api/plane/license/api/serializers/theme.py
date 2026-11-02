# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.license.models import InstanceTheme


class InstanceThemeSerializer(serializers.ModelSerializer):
    # the deployment ones cannot be changed from the GUI
    is_read_only = serializers.SerializerMethodField()

    class Meta:
        model = InstanceTheme
        fields = ["id", "name", "primary", "background", "dark_palette", "overrides", "source", "is_read_only"]
        read_only_fields = fields

    def get_is_read_only(self, obj):
        return obj.source == InstanceTheme.Source.DEPLOYMENT
