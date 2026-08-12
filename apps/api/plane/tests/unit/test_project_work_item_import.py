# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026 Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from datetime import date

import pytest

from plane.db.models import Issue, IssueAssignee, IssueSequence, Label, Project, ProjectMember, State
from plane.utils.project_work_item_import import import_work_items_into_project


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
        assert any("missing@example.com" in w and "unassigned" in w for w in result["warnings"])

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
        assert len([w for w in result["warnings"] if "unassigned" in w]) == 2

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
