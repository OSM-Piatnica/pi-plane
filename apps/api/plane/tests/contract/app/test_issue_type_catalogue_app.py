# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the type catalogue, the description template of a type and the one-day rule of milestones."""

from datetime import date

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, IssueTypeKind, Project, ProjectIssueType, ProjectMember
from plane.utils.issue_type_catalogue import CATALOGUE_KEYS

CATALOGUE_URL = "/api/workspaces/{slug}/issue-types/catalogue/"
ISSUE_TYPE_URL = "/api/workspaces/{slug}/issue-types/{pk}/"
ISSUE_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
ISSUES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"
ISSUE_DATES_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-dates/"
PUBLIC_ISSUE_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Plan", identifier="PLN", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def milestone_type(db, workspace, project):
    milestone = IssueType.objects.create(workspace=workspace, name="Milestone", kind=IssueTypeKind.MILESTONE)
    ProjectIssueType.objects.create(project=project, issue_type=milestone, workspace=workspace)
    return milestone


@pytest.fixture
def task_type(db, workspace, project):
    task = IssueType.objects.create(workspace=workspace, name="Task")
    ProjectIssueType.objects.create(project=project, issue_type=task, workspace=workspace)
    return task


def _issue(project, author, issue_type=None, **dates):
    issue = Issue(name="Go-live", project=project, workspace=project.workspace, type=issue_type, **dates)
    issue.save(created_by_id=author.id)
    return issue


@pytest.mark.contract
class TestCatalogueEndpoint:
    @pytest.mark.django_db
    def test_lists_the_entries_in_the_language_asked_for(self, session_client, workspace):
        response = session_client.get(CATALOGUE_URL.format(slug=workspace.slug), {"language": "pl"})
        assert response.status_code == status.HTTP_200_OK
        assert [row["key"] for row in response.data] == list(CATALOGUE_KEYS)
        bug = response.data[1]
        assert bug["name"] == "Błąd"
        assert bug["existing_type_id"] is None
        assert [prop["title"] for prop in bug["properties"]] == ["Waga", "Środowisko", "Kroki do odtworzenia"]

    @pytest.mark.django_db
    def test_adds_entries_and_reports_what_existed(self, session_client, workspace):
        url = CATALOGUE_URL.format(slug=workspace.slug)
        first = session_client.post(url, {"keys": ["bug", "milestone"]}, format="json")
        assert first.status_code == status.HTTP_200_OK, first.data
        assert [(row["key"], row["status"]) for row in first.data] == [("bug", "created"), ("milestone", "created")]
        assert first.data[1]["issue_type"]["kind"] == "milestone"
        assert first.data[0]["issue_type"]["description_template"]

        again = session_client.post(url, {"keys": ["bug"]}, format="json")
        assert [row["status"] for row in again.data] == ["exists"]
        listed = session_client.get(url).data
        # `response.data` holds the serializer's UUID before rendering; on the wire both are strings
        assert listed[1]["existing_type_id"] == str(first.data[0]["issue_type"]["id"])

    @pytest.mark.django_db
    @pytest.mark.parametrize("keys", [None, [], ["nope"], "bug", [1]])
    def test_bad_keys_are_refused(self, session_client, workspace, keys):
        response = session_client.post(CATALOGUE_URL.format(slug=workspace.slug), {"keys": keys}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["allowed"] == list(CATALOGUE_KEYS)
        assert not IssueType.objects.filter(workspace=workspace).exists()


@pytest.mark.contract
class TestDescriptionTemplate:
    @pytest.mark.django_db
    def test_is_saved_sanitised_and_cleared(self, session_client, workspace):
        bug = IssueType.objects.create(workspace=workspace, name="Bug")
        url = ISSUE_TYPE_URL.format(slug=workspace.slug, pk=bug.id)

        response = session_client.patch(
            url, {"description_template": "<h3>Steps</h3><script>alert(1)</script>"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        bug.refresh_from_db()
        assert bug.description_template.startswith("<h3>Steps</h3>")
        assert "<script" not in bug.description_template
        assert response.data["description_template"] == bug.description_template

        response = session_client.patch(url, {"description_template": ""}, format="json")
        assert response.status_code == status.HTTP_200_OK
        bug.refresh_from_db()
        assert bug.description_template is None


@pytest.mark.contract
class TestMilestoneDates:
    @pytest.mark.django_db
    def test_the_start_follows_the_finish_and_the_due_date_stays(
        self, session_client, workspace, project, milestone_type, create_user
    ):
        milestone = _issue(project, create_user, milestone_type)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=milestone.id),
            {"finish_date": "2026-03-06", "target_date": "2026-03-04"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        milestone.refresh_from_db()
        assert milestone.start_date == milestone.finish_date == date(2026, 3, 6)
        assert milestone.target_date == date(2026, 3, 4)
        assert milestone.duration == 1

    @pytest.mark.django_db
    def test_creating_a_milestone_with_a_range_keeps_the_finish(
        self, session_client, workspace, project, milestone_type
    ):
        response = session_client.post(
            ISSUES_URL.format(slug=workspace.slug, project_id=project.id),
            {
                "name": "Launch",
                "type_id": str(milestone_type.id),
                "start_date": "2026-03-02",
                "finish_date": "2026-03-06",
                "duration": 5,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Issue.objects.get(pk=response.data["id"])
        assert str(created.start_date) == str(created.finish_date) == "2026-03-06"
        assert created.duration == 1

    @pytest.mark.django_db
    def test_a_work_item_that_becomes_a_milestone_collapses(
        self, session_client, workspace, project, milestone_type, task_type, create_user
    ):
        task = _issue(project, create_user, task_type, start_date=date(2026, 3, 2), finish_date=date(2026, 3, 6))
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=task.id),
            {"type_id": str(milestone_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        task.refresh_from_db()
        assert str(task.start_date) == str(task.finish_date) == "2026-03-06"

    @pytest.mark.django_db
    def test_a_timeline_resize_keeps_one_day(self, session_client, workspace, project, milestone_type, create_user):
        milestone = _issue(
            project, create_user, milestone_type, start_date=date(2026, 3, 4), finish_date=date(2026, 3, 4)
        )
        response = session_client.post(
            ISSUE_DATES_URL.format(slug=workspace.slug, project_id=project.id),
            {"updates": [{"id": str(milestone.id), "finish_date": "2026-03-10"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        milestone.refresh_from_db()
        assert str(milestone.start_date) == str(milestone.finish_date) == "2026-03-10"
        assert milestone.duration == 1

    @pytest.mark.django_db
    def test_the_public_api(self, api_key_client, workspace, project, milestone_type, create_user):
        milestone = _issue(project, create_user, milestone_type)
        response = api_key_client.patch(
            PUBLIC_ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=milestone.id),
            {"start_date": "2026-03-02"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        milestone.refresh_from_db()
        assert str(milestone.start_date) == str(milestone.finish_date) == "2026-03-02"

    @pytest.mark.django_db
    def test_other_kinds_keep_their_range(self, session_client, workspace, project, task_type, create_user):
        task = _issue(project, create_user, task_type)
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=task.id),
            {"start_date": "2026-03-02", "finish_date": "2026-03-06"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        task.refresh_from_db()
        assert (str(task.start_date), str(task.finish_date)) == ("2026-03-02", "2026-03-06")
