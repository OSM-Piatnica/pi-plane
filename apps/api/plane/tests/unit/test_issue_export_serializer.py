# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

import pytest

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueRelation,
    IssueSubscriber,
    Project,
    ProjectMember,
    State,
    User,
)
from plane.utils.exporters.schemas.issue import IssueExportSchema
from plane.utils.porters.formatters import XLSXFormatter
from plane.utils.porters.serializers.issue import IssueExportSerializer


@pytest.fixture
def export_project(db, workspace, create_user):
    project = Project.objects.create(
        name="Export Serializer",
        identifier="EXS",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    State.objects.create(
        name="Todo",
        color="#60646C",
        project=project,
        workspace=workspace,
        group="unstarted",
        default=True,
        sequence=10000,
    )
    return project


def _make_issue(project, user, name, sequence_id):
    return Issue.objects.create(
        project=project,
        workspace=project.workspace,
        name=name,
        sequence_id=sequence_id,
        created_by=user,
    )


@pytest.mark.unit
class TestIssueExportSerializerPeople:
    @pytest.mark.django_db
    def test_assignees_and_subscribers_are_exported_as_emails(self, export_project, create_user):
        issue = _make_issue(export_project, create_user, "With people", 1)
        # .add() bypasses IssueAssignee.save(), which is what fills in project_id
        IssueAssignee.objects.create(
            issue=issue,
            assignee=create_user,
            project=export_project,
            workspace=export_project.workspace,
        )
        IssueSubscriber.objects.create(
            issue=issue,
            subscriber=create_user,
            project=export_project,
            workspace=export_project.workspace,
        )

        data = IssueExportSerializer(issue).data

        assert data["assignees"] == [create_user.email]
        assert data["subscribers"] == [create_user.email]

    @pytest.mark.django_db
    def test_someone_who_was_unassigned_is_not_exported(self, export_project, create_user):
        """Unassigning soft deletes the row, and the export must not resurrect it."""
        issue = _make_issue(export_project, create_user, "Assigned once", 2)
        former = User.objects.create(
            email="former@example.com",
            username="former@example.com",
            display_name="former",
        )
        ProjectMember.objects.create(project=export_project, member=former, role=15, is_active=True)
        IssueAssignee.objects.create(
            issue=issue,
            assignee=former,
            project=export_project,
            workspace=export_project.workspace,
        )
        IssueAssignee.objects.create(
            issue=issue,
            assignee=create_user,
            project=export_project,
            workspace=export_project.workspace,
        )

        # The same soft delete the work item API performs when assignees are edited
        IssueAssignee.objects.filter(issue=issue, assignee=former).delete()

        data = IssueExportSerializer(issue).data

        assert data["assignees"] == [create_user.email]


@pytest.mark.unit
class TestIssueExportSerializerRelations:
    @pytest.mark.django_db
    def test_mirror_side_of_a_relation_is_exported_with_the_inverse_type(self, export_project, create_user):
        blocked = _make_issue(export_project, create_user, "Blocked", 1)
        blocker = _make_issue(export_project, create_user, "Blocker", 2)
        IssueRelation.objects.create(
            issue=blocked,
            related_issue=blocker,
            relation_type="blocked_by",
            project=export_project,
            workspace=export_project.workspace,
        )

        blocked_relations = IssueExportSerializer(blocked).data["relations"]
        blocker_relations = IssueExportSerializer(blocker).data["relations"]

        assert blocked_relations == [{"type": "blocked_by", "issue": "EXS-2"}]
        assert blocker_relations == [{"type": "blocking", "issue": "EXS-1"}]

    @pytest.mark.django_db
    def test_symmetric_relation_keeps_its_type_on_both_sides(self, export_project, create_user):
        first = _make_issue(export_project, create_user, "First", 1)
        second = _make_issue(export_project, create_user, "Second", 2)
        IssueRelation.objects.create(
            issue=first,
            related_issue=second,
            relation_type="relates_to",
            project=export_project,
            workspace=export_project.workspace,
        )

        assert IssueExportSerializer(first).data["relations"] == [{"type": "relates_to", "issue": "EXS-2"}]
        assert IssueExportSerializer(second).data["relations"] == [{"type": "relates_to", "issue": "EXS-1"}]

    @pytest.mark.django_db
    def test_a_lag_is_exported_with_the_relation_on_both_sides_and_only_when_there_is_one(
        self, export_project, create_user
    ):
        blocked = _make_issue(export_project, create_user, "Blocked", 1)
        blocker = _make_issue(export_project, create_user, "Blocker", 2)
        other = _make_issue(export_project, create_user, "Other", 3)
        for first, second, relation_type, lag in [
            (blocked, blocker, "blocked_by", 3),
            (blocked, other, "relates_to", 0),
        ]:
            IssueRelation.objects.create(
                issue=first,
                related_issue=second,
                relation_type=relation_type,
                lag_days=lag,
                project=export_project,
                workspace=export_project.workspace,
            )

        blocked_relations = IssueExportSerializer(blocked).data["relations"]
        blocker_relations = IssueExportSerializer(blocker).data["relations"]

        assert {"type": "blocked_by", "issue": "EXS-2", "lag_days": 3} in blocked_relations
        assert {"type": "relates_to", "issue": "EXS-3"} in blocked_relations
        assert blocker_relations == [{"type": "blocking", "issue": "EXS-1", "lag_days": 3}]


@pytest.mark.unit
class TestIssueExportSchemaRelations:
    """The Relations column of the table export: every work item of a type, and the lag of a relation."""

    def _relate(self, project, first, second, relation_type, lag=0):
        IssueRelation.objects.create(
            issue=first,
            related_issue=second,
            relation_type=relation_type,
            lag_days=lag,
            project=project,
            workspace=project.workspace,
        )

    @pytest.mark.django_db
    def test_several_work_items_of_one_type_are_all_listed(self, export_project, create_user):
        blocked = _make_issue(export_project, create_user, "Blocked", 1)
        first = _make_issue(export_project, create_user, "First blocker", 2)
        second = _make_issue(export_project, create_user, "Second blocker", 3)
        self._relate(export_project, blocked, first, "blocked_by")
        self._relate(export_project, blocked, second, "blocked_by")

        relations = IssueExportSchema().prepare_relations(blocked)

        assert sorted(relations["blocked_by"].split(", ")) == ["EXS-2", "EXS-3"]

    @pytest.mark.django_db
    def test_a_lag_is_written_after_the_identifier_on_both_sides(self, export_project, create_user):
        blocked = _make_issue(export_project, create_user, "Blocked", 1)
        blocker = _make_issue(export_project, create_user, "Blocker", 2)
        self._relate(export_project, blocked, blocker, "blocked_by", lag=2)

        assert IssueExportSchema().prepare_relations(blocked) == {"blocked_by": "EXS-2 (lag 2d)"}
        assert IssueExportSchema().prepare_relations(blocker) == {"blocking": "EXS-1 (lag 2d)"}

    @pytest.mark.django_db
    def test_two_types_between_the_same_pair_are_both_there(self, export_project, create_user):
        first = _make_issue(export_project, create_user, "First", 1)
        second = _make_issue(export_project, create_user, "Second", 2)
        self._relate(export_project, first, second, "relates_to")
        self._relate(export_project, first, second, "caused_by")

        assert IssueExportSchema().prepare_relations(first) == {"relates_to": "EXS-2", "caused_by": "EXS-2"}


@pytest.mark.unit
class TestXlsxNestedLists:
    def test_lists_of_objects_are_written_as_json(self):
        formatter = XLSXFormatter()
        relations = [{"type": "blocked_by", "issue": "EXS-2"}]

        assert json.loads(formatter._format_value(relations)) == relations

    def test_plain_lists_are_still_joined(self):
        formatter = XLSXFormatter()

        assert formatter._format_value(["Bug", "Urgent"]) == "Bug, Urgent"
