# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import GroupRole, UserGroup, UserGroupMember

from .user import UserLiteSerializer


class UserGroupSerializer(serializers.ModelSerializer):
    # Counted by the view, which also tells the page what the person may do with each group
    member_count = serializers.IntegerField(read_only=True, default=0)
    can_manage = serializers.BooleanField(read_only=True, default=False)
    can_delete = serializers.BooleanField(read_only=True, default=False)
    is_external = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserGroup
        fields = [
            "id",
            "name",
            "description",
            "parent",
            "source",
            "external_id",
            "is_external",
            "member_count",
            "can_manage",
            "can_delete",
            "created_at",
        ]
        read_only_fields = ["id", "source", "external_id", "created_at"]

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("A group needs a name.")
        return value


class UserGroupMemberSerializer(serializers.ModelSerializer):
    user = UserLiteSerializer(read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = UserGroupMember
        fields = ["id", "user", "group", "group_name", "role", "managed_externally", "created_at"]
        read_only_fields = fields


class UserGroupMemberWriteSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=GroupRole.values, default=GroupRole.MEMBER)
