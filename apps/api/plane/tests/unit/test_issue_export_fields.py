# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Choosing the columns of a work item export."""

import pytest

from plane.db.models import Issue, Project, ProjectMember, State
from plane.utils.community_work_item_import import is_community_work_item_export, map_community_export_rows
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.importer import DataImporter
from plane.utils.porters.serializers.issue import (
    ISSUE_EXPORT_FIELD_GROUPS,
    ISSUE_EXPORT_OPTIONAL_FIELDS,
    ISSUE_EXPORT_REQUIRED_FIELDS,
    InvalidIssueExportFields,
    IssueExportSerializer,
    resolve_issue_export_fields,
)

ALL_COLUMNS = IssueExportSerializer.Meta.fields


@pytest.fixture
def export_project(db, workspace, create_user):
    project = Project.objects.create(name="Fields", identifier="FLD", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    State.objects.create(
        name="Todo", color="#60646C", project=project, workspace=workspace, group="unstarted", default=True, sequence=1
    )
    return project


@pytest.mark.unit
class TestFieldCatalogue:
    def test_groups_and_required_columns_are_exactly_the_columns_of_the_export(self):
        """A column added to the serializer must be placed in a group, or it cannot be chosen."""
        grouped = list(ISSUE_EXPORT_OPTIONAL_FIELDS)
        assert len(grouped) == len(set(grouped)), "a column is listed in two groups"
        assert sorted(grouped + list(ISSUE_EXPORT_REQUIRED_FIELDS)) == sorted(ALL_COLUMNS)

    def test_every_group_has_columns(self):
        assert all(ISSUE_EXPORT_FIELD_GROUPS.values())


@pytest.mark.unit
class TestResolveFields:
    def test_no_choice_means_every_column(self):
        assert resolve_issue_export_fields(None) is None

    def test_required_columns_are_always_kept(self):
        assert resolve_issue_export_fields([]) == [name for name in ALL_COLUMNS if name in ISSUE_EXPORT_REQUIRED_FIELDS]

    def test_columns_follow_the_order_of_the_export_not_of_the_request(self):
        result = resolve_issue_export_fields(["priority", "assignees", "state_name"])

        assert result == [
            name for name in ALL_COLUMNS if name in {"priority", "assignees", "state_name", "identifier", "name"}
        ]

    def test_naming_a_required_column_is_harmless(self):
        assert resolve_issue_export_fields(["name"]) == resolve_issue_export_fields([])

    def test_an_unknown_column_is_rejected_by_name(self):
        with pytest.raises(InvalidIssueExportFields, match="bogus") as raised:
            resolve_issue_export_fields(["priority", "bogus"])

        assert raised.value.unknown == ["bogus"]

    @pytest.mark.parametrize("value", ["priority", {"priority": True}, [1], [None]])
    def test_anything_but_a_list_of_names_is_rejected(self, value):
        with pytest.raises(ValueError):
            resolve_issue_export_fields(value)

    def test_every_optional_column_can_be_chosen(self):
        assert resolve_issue_export_fields(list(ISSUE_EXPORT_OPTIONAL_FIELDS)) == list(ALL_COLUMNS)


@pytest.mark.unit
class TestRestrictedExport:
    @pytest.mark.django_db
    def test_only_the_chosen_columns_are_written(self, export_project, create_user):
        Issue.objects.create(
            project=export_project, workspace=export_project.workspace, name="One", created_by=create_user
        )
        fields = resolve_issue_export_fields(["priority"])

        rows = DataExporter(IssueExportSerializer, export_fields=fields).serialize(Issue.objects.all())

        assert list(rows[0].keys()) == ["identifier", "name", "priority"]

    @pytest.mark.django_db
    def test_without_a_choice_every_column_is_written(self, export_project, create_user):
        Issue.objects.create(
            project=export_project, workspace=export_project.workspace, name="One", created_by=create_user
        )

        rows = DataExporter(IssueExportSerializer).serialize(Issue.objects.all())

        assert list(rows[0].keys()) == ALL_COLUMNS

    @pytest.mark.django_db
    @pytest.mark.parametrize("format_type", ["csv", "json", "xlsx"])
    def test_a_file_with_only_the_required_columns_can_be_imported_again(
        self, export_project, create_user, format_type
    ):
        """The reason those columns cannot be switched off."""
        parent = Issue.objects.create(
            project=export_project, workspace=export_project.workspace, name="Parent", created_by=create_user
        )
        Issue.objects.create(
            project=export_project,
            workspace=export_project.workspace,
            name="Child",
            parent=parent,
            created_by=create_user,
        )
        exporter = DataExporter(
            IssueExportSerializer,
            format_type=format_type,
            export_fields=resolve_issue_export_fields([]),
        )

        _, content = exporter.export("export", Issue.objects.order_by("sequence_id"))
        rows = DataImporter(format_type=format_type).decode(content)

        assert is_community_work_item_export(rows)
        mapped = map_community_export_rows(rows)
        assert [row["name"] for row in mapped] == ["Parent", "Child"]
        assert [row["external_key"] for row in mapped] == ["FLD-1", "FLD-2"]
