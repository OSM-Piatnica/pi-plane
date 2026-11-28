# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import Initiative, InitiativeKind, InitiativeUpdate, WorkspaceMember
from plane.utils.content_validator import validate_html_content

from .user import UserLiteSerializer


class InitiativeSerializer(serializers.ModelSerializer):
    """A goal or an initiative. The view adds the linked projects and Epics and the progress for the requester.

    Needs ``workspace_id`` in the context to check the parent and the lead.
    """

    class Meta:
        model = Initiative
        fields = [
            "id",
            "workspace",
            "kind",
            "parent",
            "name",
            "description",
            "description_html",
            "lead",
            "start_date",
            "target_date",
            "status",
            "health",
            "logo_props",
            "color",
            "sort_order",
            "created_at",
            "updated_at",
            "created_by",
        ]
        # The health is set only by a status update (``InitiativeUpdate``), which says who judged it, when and why
        read_only_fields = ["id", "workspace", "health", "created_at", "updated_at", "created_by"]

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("A name is required.")
        return value

    def validate_description_html(self, value):
        if not value:
            return "<p></p>"
        is_valid, error, clean = validate_html_content(str(value))
        if not is_valid:
            raise serializers.ValidationError(error or "Invalid HTML.")
        return clean if clean is not None else value

    def validate_logo_props(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected an object.")
        return value

    def validate(self, attrs):
        workspace_id = self.context["workspace_id"]
        instance = self.instance

        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(instance, field) if instance is not None else None

        kind = attrs.get("kind", instance.kind if instance is not None else InitiativeKind.INITIATIVE)
        if instance is not None and kind != instance.kind:
            raise serializers.ValidationError({"kind": "The kind cannot be changed."})

        parent = current("parent")
        if parent is not None:
            if kind == InitiativeKind.GOAL:
                raise serializers.ValidationError({"parent": "A goal cannot have a parent."})
            if parent.workspace_id != workspace_id or parent.kind != InitiativeKind.GOAL:
                raise serializers.ValidationError({"parent": "The parent must be a goal of this workspace."})

        lead = attrs.get("lead")
        if (
            lead is not None
            and not WorkspaceMember.objects.filter(workspace_id=workspace_id, member=lead, is_active=True).exists()
        ):
            raise serializers.ValidationError({"lead": "The lead must be a member of this workspace."})

        start_date, target_date = current("start_date"), current("target_date")
        if start_date and target_date and start_date > target_date:
            raise serializers.ValidationError({"target_date": "The target date cannot be before the start date."})
        return attrs


class InitiativeUpdateSerializer(serializers.ModelSerializer):
    author_detail = UserLiteSerializer(source="author", read_only=True)

    class Meta:
        model = InitiativeUpdate
        fields = ["id", "initiative", "author", "author_detail", "health", "text", "created_at"]
        read_only_fields = ["id", "initiative", "author", "created_at"]
