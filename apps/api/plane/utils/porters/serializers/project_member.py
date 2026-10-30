# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers


class ProjectMemberExportSerializer(serializers.Serializer):
    """
    One row of the members export: a person or a project group, as a plain dict built by
    ``plane.utils.project_member_export.project_member_export_rows``.

    ``email``, ``group`` and ``role`` are what the members CSV import reads; the other columns are
    information it ignores. The field order is the column order of the file.
    """

    email = serializers.CharField(allow_blank=True)
    group = serializers.CharField(allow_blank=True)
    role = serializers.IntegerField()
    name = serializers.CharField(allow_blank=True)
    source = serializers.CharField()
    via_group = serializers.CharField(allow_blank=True)
    raised_by_group = serializers.CharField(allow_blank=True)
    joined = serializers.CharField(allow_blank=True)
