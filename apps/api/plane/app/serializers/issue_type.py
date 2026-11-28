# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

from rest_framework import serializers

from plane.app.serializers.base import BaseSerializer
from plane.db.models import IssueType, IssueTypeKind, IssueTypeProperty, Project, ProjectIssueType, Workspace
from plane.utils.content_validator import validate_html_content
from plane.utils.issue_type_property import clean_property_list
from plane.utils.project_issue_types import (
    SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS,
    SYSTEM_MANAGED_TYPE_DEACTIVATE,
    is_system_managed_type,
    issue_type_in_use,
    refuse_system_managed_type,
)


class IssueTypePropertySerializer(BaseSerializer):
    class Meta:
        model = IssueTypeProperty
        fields = [
            "id",
            "title",
            "description",
            "property_type",
            "is_mandatory",
            "is_active",
            "sort_order",
            "options",
            "select_mode",
            "default_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sort_order", "created_at", "updated_at"]


LOGO_TEXT_MAX_LENGTH = 64
# A description template is a short skeleton (headings, a list); a whole document does not belong in a type
DESCRIPTION_TEMPLATE_MAX_LENGTH = 65536


def _logo_text(value, field):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > LOGO_TEXT_MAX_LENGTH:
        raise serializers.ValidationError(f"{field} must be text of at most {LOGO_TEXT_MAX_LENGTH} characters")
    return value


class IssueTypeSerializer(BaseSerializer):
    properties = serializers.SerializerMethodField()
    project_ids = serializers.ListField(child=serializers.UUIDField(), required=False, write_only=True)

    class Meta:
        model = IssueType
        fields = [
            "id",
            "name",
            "description",
            "description_template",
            "logo_props",
            "is_epic",
            "kind",
            "is_default",
            "is_active",
            "level",
            "properties",
            "project_ids",
            "created_at",
            "updated_at",
        ]
        # The kind is set by code: only `is_epic` moves a type between the standard and the Epic kind
        read_only_fields = ["id", "kind", "created_at", "updated_at", "properties"]

    def validate_logo_props(self, value):
        """Accept only the emoji or icon shape that the web logo renderer understands.

        The logo is shown next to the identifier of every work item of the type, so what is stored must be a short
        emoji or icon name and colours, nothing else. An empty value clears the logo.
        """

        if value in (None, {}):
            return {}
        if not isinstance(value, dict) or value.get("in_use") not in {"emoji", "icon"}:
            raise serializers.ValidationError("in_use must be 'emoji' or 'icon'")
        if set(value) - {"in_use", "emoji", "icon"}:
            raise serializers.ValidationError("Unsupported logo field")

        in_use = value["in_use"]
        detail = value.get(in_use)
        if not isinstance(detail, dict):
            raise serializers.ValidationError(f"{in_use} details are required")

        allowed = {"value", "url"} if in_use == "emoji" else {"name", "color", "background_color"}
        if set(detail) - allowed:
            raise serializers.ValidationError(f"Unsupported {in_use} field")
        clean = {key: _logo_text(detail.get(key), f"{in_use}.{key}") for key in allowed if key in detail}
        primary = "value" if in_use == "emoji" else "name"
        if not clean.get(primary):
            raise serializers.ValidationError(f"{in_use}.{primary} is required")
        return {"in_use": in_use, in_use: clean}

    def validate_description_template(self, value):
        """Sanitised like a work item description, since the create form copies it into one. Empty clears it."""

        if value is None or not str(value).strip():
            return None
        if len(value) > DESCRIPTION_TEMPLATE_MAX_LENGTH:
            raise serializers.ValidationError(
                f"The description template must be at most {DESCRIPTION_TEMPLATE_MAX_LENGTH} characters"
            )
        is_valid, _error, sanitized = validate_html_content(value)
        if not is_valid:
            raise serializers.ValidationError("The description template is not valid HTML")
        return sanitized if sanitized is not None else value

    def get_properties(self, instance):
        props = IssueTypeProperty.objects.filter(issue_type=instance, deleted_at__isnull=True).order_by(
            "sort_order", "created_at"
        )
        return IssueTypePropertySerializer(props, many=True).data

    def _raw_properties_from_request(self):
        if not isinstance(self.initial_data, dict):
            return None
        return self.initial_data.get("properties")

    def validate_name(self, value):
        name = str(value or "").strip()
        if not name:
            raise serializers.ValidationError("Name is required")
        slug = self.context.get("slug")
        if not slug:
            return name[:255]
        workspace = Workspace.objects.filter(slug=slug).first()
        if not workspace:
            raise serializers.ValidationError("Workspace not found")
        qs = IssueType.objects.filter(workspace_id=workspace.id, name__iexact=name, deleted_at__isnull=True)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An issue type with this name already exists")
        return name[:255]

    def _sync_properties(self, issue_type: IssueType, raw_properties):
        if raw_properties is None:
            return
        try:
            cleaned_rows = clean_property_list(raw_properties)
        except ValueError as exc:
            raise serializers.ValidationError({"properties": str(exc)})

        existing = {
            str(row.id): row for row in IssueTypeProperty.objects.filter(issue_type=issue_type, deleted_at__isnull=True)
        }
        seen_ids = set()

        for idx, row in enumerate(cleaned_rows):
            prop_id = row.get("id")
            parsed_id = None
            if prop_id:
                try:
                    parsed_id = uuid.UUID(str(prop_id))
                except (ValueError, TypeError, AttributeError):
                    parsed_id = None

            payload = {
                "title": row["title"],
                "description": row.get("description", ""),
                "property_type": row["property_type"],
                "is_mandatory": row.get("is_mandatory", False),
                "is_active": row.get("is_active", True),
                "options": row.get("options", []),
                "select_mode": row.get("select_mode", "single"),
                "default_value": row.get("default_value"),
                "sort_order": (idx + 1) * 10000,
            }

            if parsed_id and str(parsed_id) in existing:
                obj = existing[str(parsed_id)]
                for key, val in payload.items():
                    setattr(obj, key, val)
                obj.save()
                seen_ids.add(str(parsed_id))
            else:
                IssueTypeProperty.objects.create(
                    workspace_id=issue_type.workspace_id,
                    issue_type=issue_type,
                    **payload,
                )

        for key, obj in existing.items():
            if key not in seen_ids:
                obj.delete()

    def _valid_project_ids(self, project_ids) -> set:
        """The ids among `project_ids` of the workspace's projects that are neither archived nor deleted."""

        workspace = Workspace.objects.get(slug=self.context.get("slug"))
        return set(
            str(pid)
            for pid in Project.objects.filter(
                workspace_id=workspace.id,
                id__in=project_ids,
                archived_at__isnull=True,
                deleted_at__isnull=True,
            ).values_list("id", flat=True)
        )

    def _project_links_change(self, issue_type: IssueType, project_ids) -> bool:
        """Whether `_sync_project_links` would link or unlink a project that is neither archived nor deleted."""

        current = set(
            str(pid)
            for pid in ProjectIssueType.objects.filter(
                issue_type=issue_type,
                deleted_at__isnull=True,
                project__archived_at__isnull=True,
                project__deleted_at__isnull=True,
            ).values_list("project_id", flat=True)
        )
        return self._valid_project_ids(project_ids) != current

    def _sync_project_links(self, issue_type: IssueType, project_ids):
        if project_ids is None:
            return
        if is_system_managed_type(issue_type):
            # `validate` has refused any change already. The form sends back the list it got, so nothing is synced:
            # that also keeps the links to archived projects, which the sync below would drop
            return
        valid_ids = self._valid_project_ids(project_ids)
        existing = {
            str(row.project_id): row
            for row in ProjectIssueType.objects.filter(issue_type=issue_type, deleted_at__isnull=True)
        }
        for pid in valid_ids:
            if pid not in existing:
                ProjectIssueType.objects.create(
                    project_id=pid,
                    issue_type=issue_type,
                    workspace_id=issue_type.workspace_id,
                    level=issue_type.level,
                    is_default=issue_type.is_default,
                )
        for pid, row in existing.items():
            if pid not in valid_ids:
                row.delete()

    def create(self, validated_data):
        properties = self._raw_properties_from_request()
        project_ids = validated_data.pop("project_ids", None)
        slug = self.context.get("slug")
        workspace = Workspace.objects.get(slug=slug)
        validated_data["workspace_id"] = workspace.id
        if validated_data.get("logo_props") is None:
            validated_data["logo_props"] = {}
        issue_type = super().create(validated_data)
        if properties is not None:
            self._sync_properties(issue_type, properties)
        if project_ids is not None:
            self._sync_project_links(issue_type, project_ids)
        return issue_type

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # `kind` is read-only, so a type made here is always `standard` or `epic`: a system-managed type comes only
        # from `ensure_project_kind_type`. Such a type keeps its name, icon, description and properties editable;
        # it cannot be switched off, and the projects that use it are left to the feature that owns it
        if is_system_managed_type(self.instance):
            if self.instance.is_active and attrs.get("is_active", True) is False:
                refuse_system_managed_type(self.instance, SYSTEM_MANAGED_TYPE_DEACTIVATE)
            project_ids = attrs.get("project_ids")
            if project_ids is not None and self._project_links_change(self.instance, project_ids):
                refuse_system_managed_type(self.instance, SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS)
        # Work items that have a parent would silently become Epics (or Epics would stop being one), so the
        # flag is fixed as soon as a work item uses the type
        if self.instance is not None and "is_epic" in attrs and attrs["is_epic"] != self.instance.is_epic:
            if self.instance.kind not in (IssueTypeKind.STANDARD, IssueTypeKind.EPIC):
                raise serializers.ValidationError(
                    {"is_epic": f"A work item type of the {self.instance.kind} kind cannot become an Epic type"}
                )
            if issue_type_in_use(self.instance):
                raise serializers.ValidationError(
                    {"is_epic": "Cannot be changed while work items use this work item type"}
                )
        return attrs

    def update(self, instance, validated_data):
        properties = self._raw_properties_from_request()
        project_ids = validated_data.pop("project_ids", None)
        issue_type = super().update(instance, validated_data)
        if properties is not None:
            self._sync_properties(issue_type, properties)
        if project_ids is not None:
            self._sync_project_links(issue_type, project_ids)
        return issue_type

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["project_ids"] = list(
            ProjectIssueType.objects.filter(issue_type=instance, deleted_at__isnull=True).values_list(
                "project_id", flat=True
            )
        )
        return data


class ProjectIssueTypeSerializer(BaseSerializer):
    issue_type_detail = IssueTypeSerializer(source="issue_type", read_only=True)

    class Meta:
        model = ProjectIssueType
        fields = [
            "id",
            "issue_type",
            "issue_type_detail",
            "level",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["issue_type_id"] = str(instance.issue_type_id)
        if "issue_type" in data:
            del data["issue_type"]
        return data
