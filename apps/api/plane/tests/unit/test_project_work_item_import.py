# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026 Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from datetime import date

import pytest

from plane.db.models import (
    Cycle,
    CycleIssue,
    Issue,
    IssueAssignee,
    IssueRelation,
    IssueSequence,
    IssueSubscriber,
    Label,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
)
from plane.utils.project_work_item_import import import_work_items_into_project


def _project_with_state(workspace, user, name, identifier):
    project = Project.objects.create(
        name=name,
        identifier=identifier,
        workspace=workspace,
        created_by=user,
    )
    ProjectMember.objects.create(project=project, member=user, role=20, is_active=True)
    State.objects.create(
        name="Todo",
        color="#3B82F6",
        project=project,
        workspace=workspace,
        group="unstarted",
        sequence=10000,
        default=True,
        created_by=user,
    )
    return project


@pytest.mark.django_db
class TestProjectWorkItemImport:
    def test_import_creates_issues_with_parent_links(self, workspace, create_user):
        project = Project.objects.create(
            name="Import WI",
            identifier="IWI",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        state = State.objects.create(
            name="Todo",
            color="#3B82F6",
            project=project,
            workspace=workspace,
            group="unstarted",
            sequence=10000,
            default=True,
            created_by=create_user,
        )
        Label.objects.create(
            name="Bug",
            color="#EF4444",
            project=project,
            workspace=workspace,
            created_by=create_user,
        )

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "P1",
                    "name": "Parent",
                    "description_html": "<p>Parent</p>",
                    "state": "Todo",
                    "priority": "high",
                    "labels": ["Bug"],
                    "assignee_emails": [create_user.email],
                },
                {
                    "external_key": "C1",
                    "name": "Child",
                    "description_html": "plain text child",
                    "state": "Todo",
                    "priority": "low",
                    "parent_external_key": "P1",
                    "labels": [],
                    "assignee_emails": ["missing@example.com"],
                },
            ],
        )

        assert result["created_work_items"] == 2
        assert any("missing@example.com" in w and "skipped" in w for w in result["warnings"])

        parent = Issue.objects.get(project=project, name="Parent")
        assert IssueAssignee.objects.filter(issue=parent, assignee=create_user).exists()

        child = Issue.objects.get(project=project, name="Child")
        assert child.parent is not None
        assert child.parent.name == "Parent"
        assert child.description_html.startswith("<p>")
        assert not IssueAssignee.objects.filter(issue=child).exists()
        assert IssueSequence.objects.filter(project=project).count() == 2

    def test_unknown_assignee_email_does_not_fail_import(self, workspace, create_user):
        project = Project.objects.create(
            name="Unassigned WI",
            identifier="UNA",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        State.objects.create(
            name="Todo",
            color="#3B82F6",
            project=project,
            workspace=workspace,
            group="unstarted",
            sequence=10000,
            default=True,
            created_by=create_user,
        )

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "A1",
                    "name": "Alone",
                    "state": "Todo",
                    "priority": "none",
                    "assignee_emails": ["nobody@example.com", "also-missing@example.com"],
                }
            ],
        )

        assert result["created_work_items"] == 1
        issue = Issue.objects.get(project=project, name="Alone")
        assert not IssueAssignee.objects.filter(issue=issue).exists()
        assert len([w for w in result["warnings"] if "is not a member of this workspace" in w]) == 2

    def test_duration_is_kept_consistent_with_the_dates(self, workspace, create_user):
        project = Project.objects.create(
            name="Duration WI",
            identifier="DUR",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        State.objects.create(
            name="Todo",
            color="#3B82F6",
            project=project,
            workspace=workspace,
            group="unstarted",
            sequence=10000,
            default=True,
            created_by=create_user,
        )

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "D1",
                    "name": "Exported duration",
                    "state": "Todo",
                    "start_date": "2026-03-02",
                    "target_date": "2026-03-06",
                    "duration": 5,
                },
                {
                    "external_key": "D2",
                    "name": "Derived from dates",
                    "state": "Todo",
                    "start_date": "2026-03-02",
                    "target_date": "2026-03-04",
                },
                {
                    "external_key": "D3",
                    "name": "Derived target date",
                    "state": "Todo",
                    "start_date": "2026-03-02",
                    "duration": "4",
                },
                {
                    "external_key": "D4",
                    "name": "Standalone duration",
                    "state": "Todo",
                    "duration": 7,
                },
                {
                    "external_key": "D5",
                    "name": "Unreadable duration",
                    "state": "Todo",
                    "start_date": "2026-03-02",
                    "target_date": "2026-03-04",
                    "duration": "five days",
                },
            ],
        )

        assert result["created_work_items"] == 5
        assert Issue.objects.get(project=project, name="Exported duration").duration == 5

        derived = Issue.objects.get(project=project, name="Derived from dates")
        assert derived.duration == 3

        anchored = Issue.objects.get(project=project, name="Derived target date")
        assert anchored.duration == 4
        assert anchored.target_date == date(2026, 3, 5)

        standalone = Issue.objects.get(project=project, name="Standalone duration")
        assert standalone.duration == 7
        assert standalone.start_date is None
        assert standalone.target_date is None

        unreadable = Issue.objects.get(project=project, name="Unreadable duration")
        assert unreadable.duration == 3
        assert any("five days" in w for w in result["warnings"])


@pytest.mark.django_db
class TestWorkItemImportCreatesMissingEntities:
    def test_missing_labels_and_modules_are_created(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Fresh", "FRS")

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "FRS-1",
                    "name": "Needs a label",
                    "state": "Todo",
                    "labels": ["Nawozy", "Social media"],
                    "modules": ["Kampania wiosenna"],
                }
            ],
        )

        assert result["created_work_items"] == 1
        assert Label.objects.filter(project=project, name="Nawozy").exists()
        assert Label.objects.filter(project=project, name="Social media").exists()
        assert Module.objects.filter(project=project, name="Kampania wiosenna").exists()

        issue = Issue.objects.get(project=project, name="Needs a label")
        assert ModuleIssue.objects.filter(issue=issue).count() == 1
        assert any("label" in w for w in result["warnings"])

    def test_existing_label_is_reused_not_duplicated(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Reuse", "REU")
        Label.objects.create(name="Bug", color="#EF4444", project=project, workspace=workspace)

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "R1", "name": "One", "state": "Todo", "labels": ["bug"]}],
        )

        assert Label.objects.filter(project=project, name__iexact="bug").count() == 1

    def test_missing_cycle_is_created_with_dates_from_its_work_items(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Cycles", "CYC")

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "C1",
                    "name": "Early",
                    "state": "Todo",
                    "cycles": ["Sprint 1"],
                    "start_date": "2026-03-02",
                    "target_date": "2026-03-06",
                },
                {
                    "external_key": "C2",
                    "name": "Late",
                    "state": "Todo",
                    "cycles": ["Sprint 1"],
                    "start_date": "2026-03-04",
                    "target_date": "2026-03-20",
                },
            ],
        )

        cycle = Cycle.objects.get(project=project, name="Sprint 1")
        assert cycle.start_date.date() == date(2026, 3, 2)
        assert cycle.end_date.date() == date(2026, 3, 20)
        assert CycleIssue.objects.filter(cycle=cycle).count() == 2
        assert any("Sprint 1" in w for w in result["warnings"])

    def test_cycle_without_dated_work_items_is_created_as_a_draft(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Draft cycle", "DRC")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "D1", "name": "No dates", "state": "Todo", "cycles": ["Backlog sprint"]}],
        )

        cycle = Cycle.objects.get(project=project, name="Backlog sprint")
        assert cycle.start_date is None
        assert cycle.end_date is None
        assert CycleIssue.objects.filter(cycle=cycle).count() == 1

    def test_existing_cycle_is_attached(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Has cycle", "HCY")
        Cycle.objects.create(name="Sprint 1", project=project, workspace=workspace, owned_by=create_user)

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "C1", "name": "In cycle", "state": "Todo", "cycles": ["Sprint 1"]}],
        )

        issue = Issue.objects.get(project=project, name="In cycle")
        assert CycleIssue.objects.filter(issue=issue).count() == 1


@pytest.mark.django_db
class TestWorkItemImportPeople:
    def test_assignee_matches_by_full_name_not_only_display_name(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Names", "NAM")
        create_user.first_name = "Jan"
        create_user.last_name = "Kowalski"
        create_user.display_name = "jan.kowalski"
        create_user.save()

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "N1", "name": "By full name", "state": "Todo", "assignees": ["Jan Kowalski"]}],
        )

        issue = Issue.objects.get(project=project, name="By full name")
        assert IssueAssignee.objects.filter(issue=issue, assignee=create_user).exists()

    def test_subscribers_are_imported(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Subs", "SUB")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "S1", "name": "Watched", "state": "Todo", "subscribers": [create_user.email]}],
        )

        issue = Issue.objects.get(project=project, name="Watched")
        assert IssueSubscriber.objects.filter(issue=issue, subscriber=create_user).exists()


@pytest.mark.django_db
class TestWorkItemImportRelations:
    def test_mirrored_relation_is_stored_on_the_canonical_side(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Relations", "REL")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "REL-1",
                    "name": "Blocker",
                    "state": "Todo",
                    "relations": [{"type": "blocking", "issue": "REL-2"}],
                },
                {"external_key": "REL-2", "name": "Blocked", "state": "Todo"},
            ],
        )

        blocker = Issue.objects.get(project=project, name="Blocker")
        blocked = Issue.objects.get(project=project, name="Blocked")
        relation = IssueRelation.objects.get(project=project)

        assert relation.relation_type == "blocked_by"
        assert relation.issue_id == blocked.id
        assert relation.related_issue_id == blocker.id

    def test_relation_written_on_both_sides_creates_one_row(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Both", "BTH")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "BTH-1",
                    "name": "First",
                    "state": "Todo",
                    "relations": [{"type": "blocked_by", "issue": "BTH-2"}],
                },
                {
                    "external_key": "BTH-2",
                    "name": "Second",
                    "state": "Todo",
                    "relations": [{"type": "blocking", "issue": "BTH-1"}],
                },
            ],
        )

        assert IssueRelation.objects.filter(project=project).count() == 1

    def test_symmetric_relation_is_not_duplicated(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Symmetric", "SYM")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "SYM-1",
                    "name": "First",
                    "state": "Todo",
                    "relations": [{"type": "relates_to", "issue": "SYM-2"}],
                },
                {
                    "external_key": "SYM-2",
                    "name": "Second",
                    "state": "Todo",
                    "relations": [{"type": "relates_to", "issue": "SYM-1"}],
                },
            ],
        )

        assert IssueRelation.objects.filter(project=project).count() == 1

    def test_relation_to_an_existing_work_item_is_resolved(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Existing", "EXI")
        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[{"external_key": "EXI-1", "name": "Already here", "state": "Todo"}],
        )
        first = Issue.objects.get(project=project, name="Already here")

        import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "EXI-2",
                    "name": "Newcomer",
                    "state": "Todo",
                    "relations": [{"type": "relates_to", "issue": f"EXI-{first.sequence_id}"}],
                }
            ],
        )

        assert IssueRelation.objects.filter(project=project).count() == 1


@pytest.mark.django_db
class TestWorkItemImportDates:
    def test_unreadable_date_is_reported_and_does_not_break_the_import(self, workspace, create_user):
        project = _project_with_state(workspace, create_user, "Dates", "DAT")

        result = import_work_items_into_project(
            project=project,
            user=create_user,
            rows=[
                {
                    "external_key": "D1",
                    "name": "Bad date",
                    "state": "Todo",
                    "start_date": "01.03.2026",
                }
            ],
        )

        assert result["created_work_items"] == 1
        assert Issue.objects.get(project=project, name="Bad date").start_date is None
        assert any("01.03.2026" in w for w in result["warnings"])
