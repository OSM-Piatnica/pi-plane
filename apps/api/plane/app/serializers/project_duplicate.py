# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the project duplication of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

# Python imports
import re

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Project, ProjectCopyJob
from plane.db.models.project import ProjectNetwork
from plane.utils.project_copy_work_items import InvalidWorkItemProperties, resolve_work_item_properties
from plane.utils.project_duplicate import COPY_OPTIONS


class ProjectCopyOptionsSerializer(serializers.Serializer):
    """What to carry across.

    Declared field by field rather than as a free-form JSONField: the opt-in
    surface of a copy should be auditable, and an unknown key is a mistake worth
    reporting rather than a silently ignored no-op.
    """

    states = serializers.BooleanField(required=False)
    work_item_types = serializers.BooleanField(required=False)
    labels = serializers.BooleanField(required=False)
    estimates = serializers.BooleanField(required=False)
    intake = serializers.BooleanField(required=False)
    members = serializers.BooleanField(required=False)
    cycles = serializers.BooleanField(required=False)
    modules = serializers.BooleanField(required=False)
    views = serializers.BooleanField(required=False)
    work_items = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("include must be an object")

        unknown = sorted(set(data) - set(COPY_OPTIONS))
        if unknown:
            raise serializers.ValidationError(f"Unknown copy option(s): {', '.join(unknown)}")

        return super().to_internal_value(data)


class ProjectDuplicateSerializer(serializers.Serializer):
    """Request body for duplicating a project.

    Every field is optional; the service derives a free name and identifier and
    inherits the source's visibility when they are omitted.
    """

    name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    identifier = serializers.CharField(required=False, allow_blank=False, max_length=12)
    network = serializers.ChoiceField(required=False, choices=ProjectNetwork.choices())
    include = ProjectCopyOptionsSerializer(required=False)
    # Which parts of the work items to carry; only used when `include.work_items` is on
    work_item_properties = serializers.ListField(child=serializers.CharField(), required=False)

    def validate_name(self, name):
        name = name.strip()
        if not name or re.match(Project.FORBIDDEN_NAME_CHARS_PATTERN, name):
            raise serializers.ValidationError("PROJECT_NAME_CANNOT_CONTAIN_SPECIAL_CHARACTERS")
        return name

    def validate_work_item_properties(self, value):
        try:
            return resolve_work_item_properties(value)
        except InvalidWorkItemProperties as error:
            # Built from the names, not from the exception text
            if error.unknown:
                raise serializers.ValidationError(f"Unknown work item properties: {', '.join(error.unknown)}")
            raise serializers.ValidationError("work_item_properties must be a list of names")

    def validate_identifier(self, identifier):
        identifier = identifier.strip().upper()
        if re.match(Project.FORBIDDEN_IDENTIFIER_CHARS_PATTERN, identifier):
            raise serializers.ValidationError("PROJECT_IDENTIFIER_CANNOT_CONTAIN_SPECIAL_CHARACTERS")
        return identifier


class ProjectCopyJobSerializer(serializers.ModelSerializer):
    """What the interface needs to report a copy in progress.

    Read-only throughout: nothing about a running copy is client-settable. The lease, the cursor and
    the stored translation are machinery and are not exposed.
    """

    class Meta:
        model = ProjectCopyJob
        fields = [
            "id",
            "status",
            "stage",
            "total",
            "copied",
            "counts",
            "skipped",
            "errors",
            "reason",
            "started_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields
