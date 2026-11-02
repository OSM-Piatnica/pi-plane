# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import ProjectGroup, ProjectGroupRole


class ProjectGroupSerializer(serializers.ModelSerializer):
    """A user group that is a member of a project, with the role it gives its people (Member or Guest)."""

    group_name = serializers.CharField(source="group.name", read_only=True)
    group_source = serializers.CharField(source="group.source", read_only=True)
    member_count = serializers.IntegerField(
        read_only=True,
        default=0,
        help_text="People who belong to the project through this group",
    )
    role = serializers.ChoiceField(choices=ProjectGroupRole.values, help_text="15 (Member) or 5 (Guest)")

    class Meta:
        model = ProjectGroup
        fields = ["id", "group", "group_name", "group_source", "role", "member_count"]
        read_only_fields = ["id"]

    def validate_role(self, value):
        if value not in ProjectGroupRole.values:
            raise serializers.ValidationError("A group can only be a Member or a Guest of a project.")
        return value


class ProjectGroupRoleUpdateSerializer(serializers.Serializer):
    """Request body of a role change."""

    role = serializers.ChoiceField(choices=ProjectGroupRole.values)
