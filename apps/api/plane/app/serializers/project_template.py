import re

from rest_framework import serializers

from plane.app.serializers.base import BaseSerializer
from plane.db.models import ProjectTemplate, Workspace
from plane.utils.project_template_payload import validate_and_clean_project_payload


class ProjectTemplateSerializer(BaseSerializer):
    class Meta:
        model = ProjectTemplate
        fields = [
            "id",
            "name",
            "description",
            "payload",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sort_order", "created_at", "updated_at"]

    def validate(self, attrs):
        slug = self.context.get("slug")
        workspace = Workspace.objects.get(slug=slug)

        name = attrs.get("name", getattr(self.instance, "name", ""))
        if not str(name).strip():
            raise serializers.ValidationError({"name": "Name is required"})

        if "payload" in attrs:
            payload = attrs.get("payload") or {}
        else:
            payload = self.instance.payload if self.instance else {}

        cleaned_payload = validate_and_clean_project_payload(payload, workspace)

        attrs["name"] = str(name).strip()[:255]
        attrs["description"] = str(attrs.get("description", getattr(self.instance, "description", "")) or "")
        attrs["payload"] = cleaned_payload
        return attrs

    def create(self, validated_data):
        slug = self.context.get("slug")
        workspace = Workspace.objects.get(slug=slug)
        validated_data["workspace_id"] = workspace.id
        return super().create(validated_data)
