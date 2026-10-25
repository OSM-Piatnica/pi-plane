# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A work item export is in the order of the person's own list view."""

from unittest.mock import patch

import pytest

from plane.bgtasks.export_task import in_list_view_order, issue_export_task, list_view_order
from plane.db.models import ExporterHistory, Issue, Project, ProjectMember, ProjectUserProperty
from plane.utils.order_queryset import order_issue_queryset


def _project(workspace, user, identifier):
    project = Project.objects.create(name=f"Project {identifier}", identifier=identifier, workspace=workspace)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=20, is_active=True)
    return project


def _items(project, user, *names, **extra):
    return [
        Issue.objects.create(name=name, project=project, workspace=project.workspace, created_by=user, **extra)
        for name in names
    ]


def _choose_order(project, user, order_by):
    ProjectUserProperty.objects.update_or_create(
        project=project, user=user, defaults={"workspace": project.workspace, "display_filters": {"order_by": order_by}}
    )


def _names(queryset):
    return [issue.name for issue in queryset]


@pytest.mark.unit
@pytest.mark.django_db
class TestListViewOrder:
    def test_the_stored_order_is_read(self, workspace, create_user):
        project = _project(workspace, create_user, "ORD")
        _choose_order(project, create_user, "-sequence_id")

        assert list_view_order(create_user.id, project.id) == "-sequence_id"

    def test_newest_first_when_nothing_was_chosen(self, workspace, create_user):
        project = _project(workspace, create_user, "ORD")

        assert list_view_order(create_user.id, project.id) == "-created_at"

    @pytest.mark.parametrize("value", [None, "", 5, ["name"]])
    def test_an_unusable_value_is_treated_as_no_choice(self, workspace, create_user, value):
        project = _project(workspace, create_user, "ORD")
        _choose_order(project, create_user, value)

        assert list_view_order(create_user.id, project.id) == "-created_at"

    def test_it_is_the_order_of_that_person_only(self, workspace, create_user):
        from plane.db.models import User

        other = User.objects.create(email="other-order@example.test", username="other-order")
        project = _project(workspace, create_user, "ORD")
        _choose_order(project, create_user, "name")

        assert list_view_order(other.id, project.id) == "-created_at"

    def test_work_items_come_out_in_that_order(self, workspace, create_user):
        project = _project(workspace, create_user, "ORD")
        _items(project, create_user, "Bravo", "Alpha", "Charlie")

        _choose_order(project, create_user, "-sequence_id")
        assert _names(in_list_view_order(Issue.objects.filter(project=project), create_user.id, project.id)) == [
            "Charlie",
            "Alpha",
            "Bravo",
        ]

        _choose_order(project, create_user, "sequence_id")
        assert _names(in_list_view_order(Issue.objects.filter(project=project), create_user.id, project.id)) == [
            "Bravo",
            "Alpha",
            "Charlie",
        ]

    def test_priority_is_ordered_by_urgency_not_alphabetically(self, workspace, create_user):
        project = _project(workspace, create_user, "ORD")
        for name, priority in (("Low one", "low"), ("Urgent one", "urgent"), ("Medium one", "medium")):
            _items(project, create_user, name, priority=priority)

        _choose_order(project, create_user, "-priority")
        # the same direction convention as the list view's own endpoint
        expected = _names(
            order_issue_queryset(issue_queryset=Issue.objects.filter(project=project), order_by_param="-priority")[0]
        )

        assert _names(in_list_view_order(Issue.objects.filter(project=project), create_user.id, project.id)) == expected

    def test_a_field_that_cannot_be_ordered_by_falls_back_like_the_list_view(self, workspace, create_user):
        project = _project(workspace, create_user, "ORD")
        _items(project, create_user, "First", "Second")
        _choose_order(project, create_user, "project__workspace__owner__password")

        assert _names(in_list_view_order(Issue.objects.filter(project=project), create_user.id, project.id)) == [
            "Second",
            "First",
        ]


@pytest.mark.unit
@pytest.mark.django_db
class TestExportFollowsTheListView:
    def _export(self, workspace, user, projects, multiple):
        exporter = ExporterHistory.objects.create(
            workspace=workspace,
            project=[str(project.id) for project in projects],
            initiated_by=user,
            provider="json",
            type="issue_exports",
        )
        with (
            patch("plane.bgtasks.export_task.upload_to_s3"),
            patch("plane.bgtasks.export_task.upload_export_file_to_s3"),
            patch("plane.bgtasks.export_task.DataExporter") as data_exporter,
        ):
            data_exporter.return_value.export.side_effect = lambda name, rows: (name + ".json", "[]")
            issue_export_task(
                provider="json",
                workspace_id=workspace.id,
                project_ids=[str(project.id) for project in projects],
                token_id=exporter.token,
                multiple=multiple,
                slug=workspace.slug,
            )
        return [
            (call.args[0], [issue.name for issue in call.args[1]])
            for call in data_exporter.return_value.export.call_args_list
        ]

    def test_each_project_of_a_split_export_follows_its_own_order(self, workspace, create_user):
        first = _project(workspace, create_user, "AAA")
        second = _project(workspace, create_user, "BBB")
        _items(first, create_user, "a1", "a2")
        _items(second, create_user, "b1", "b2")
        _choose_order(first, create_user, "sequence_id")
        _choose_order(second, create_user, "-sequence_id")

        calls = self._export(workspace, create_user, [first, second], multiple=True)

        assert [names for _, names in calls] == [["a1", "a2"], ["b2", "b1"]]

    def test_a_combined_export_goes_project_by_project(self, workspace, create_user):
        first = _project(workspace, create_user, "AAA")
        second = _project(workspace, create_user, "BBB")
        _items(first, create_user, "a1", "a2")
        _items(second, create_user, "b1", "b2")
        _choose_order(first, create_user, "-sequence_id")
        _choose_order(second, create_user, "sequence_id")

        (call,) = self._export(workspace, create_user, [second, first], multiple=False)

        assert call[1] == ["a2", "a1", "b1", "b2"], "projects by identifier, each in its own list order"
