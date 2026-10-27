# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import IssueWorkLog


class IssueWorkLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueWorkLog
        fields = [
            "id",
            "duration",
            "description",
            "logged_by",
            "issue",
            "project",
            "workspace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "logged_by", "issue", "project", "workspace", "created_at", "updated_at"]
