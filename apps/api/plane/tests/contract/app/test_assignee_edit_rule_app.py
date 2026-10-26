# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: only the assignees of a work item, the project lead and the project admins may change it."""

from datetime import date
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Issue,
    IssueAssignee,
    IssueRelation,
    Project,
    ProjectMember,
    WorkspaceMember,
)
from plane.tests.factories import UserFactory

ADMIN, MEMBER = 20, 15


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch("plane.app.views.issue.link.issue_activity"),
        mock.patch("plane.app.views.issue.relation.issue_activity"),
        mock.patch("plane.app.views.issue.relation.base_host", return_value="http://testserver"),
        mock.patch("plane.app.views.issue.comment.issue_activity"),
        mock.patch("plane.app.views.issue.comment.model_activity"),
        mock.patch("plane.app.views.issue.comment.base_host", return_value="http://testserver"),
        mock.patch("plane.api.views.issue.issue_activity"),
        mock.patch("plane.api.views.issue.base_host", return_value="http://testserver"),
    ):
        yield


def person(workspace, project, role=MEMBER, workspace_role=MEMBER):
    user = UserFactory()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=workspace_role)
    ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Edit", identifier="EDT", workspace=workspace, created_by=create_user, is_assignee_edit_rule_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


@pytest.fixture
def people(workspace, project):
    return {
        "assignee": person(workspace, project),
        "other": person(workspace, project),
        "lead": person(workspace, project),
        "workspace_admin": person(workspace, project, workspace_role=ADMIN),
    }


@pytest.fixture
def assigned(workspace, project, people):
    """A work item assigned to ``assignee``, led by ``lead``."""
    Project.objects.filter(pk=project.pk).update(project_lead=people["lead"])
    issue = Issue.objects.create(name="Assigned", workspace=workspace, project=project)
    IssueAssignee.objects.create(issue=issue, assignee=people["assignee"], project=project, workspace=workspace)
    return issue


def url(workspace, project, issue, suffix=""):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/{suffix}"


def rename(user, workspace, project, issue, name="Renamed"):
    return client_for(user).patch(url(workspace, project, issue), {"name": name}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestChangingAWorkItem:
    def test_the_assignee_may(self, workspace, project, people, assigned):
        assert rename(people["assignee"], workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_the_project_lead_may_without_being_assigned(self, workspace, project, people, assigned):
        assert rename(people["lead"], workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_a_project_admin_may(self, workspace, project, create_user, assigned):
        assert rename(create_user, workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_a_workspace_admin_in_the_project_may(self, workspace, project, people, assigned):
        assert rename(people["workspace_admin"], workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_another_member_may_not(self, workspace, project, people, assigned):
        response = rename(people["other"], workspace, project, assigned)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error_code"] == "work_item_edit_restricted"
        assert response.json()["work_item_ids"] == [str(assigned.id)]
        assigned.refresh_from_db()
        assert assigned.name == "Assigned"

    def test_the_creator_is_no_exception(self, workspace, project, people):
        issue = Issue.objects.create(name="Mine", workspace=workspace, project=project, created_by=people["other"])
        IssueAssignee.objects.create(issue=issue, assignee=people["assignee"], project=project, workspace=workspace)

        assert rename(people["other"], workspace, project, issue).status_code == status.HTTP_403_FORBIDDEN

    def test_any_member_may_while_nobody_is_assigned(self, workspace, project, people):
        issue = Issue.objects.create(name="Open", workspace=workspace, project=project)

        assert rename(people["other"], workspace, project, issue).status_code == status.HTTP_204_NO_CONTENT

    def test_a_member_can_assign_an_open_item_to_themselves_and_is_then_the_only_one_besides_the_lead(
        self, workspace, project, people
    ):
        issue = Issue.objects.create(name="Open", workspace=workspace, project=project)
        taken = client_for(people["other"]).patch(
            url(workspace, project, issue), {"assignee_ids": [str(people["other"].id)]}, format="json"
        )
        outsider = rename(people["assignee"], workspace, project, issue)

        assert taken.status_code == status.HTTP_204_NO_CONTENT
        assert outsider.status_code == status.HTTP_403_FORBIDDEN

    def test_an_assignee_can_hand_the_item_over(self, workspace, project, people, assigned):
        response = client_for(people["assignee"]).patch(
            url(workspace, project, assigned), {"assignee_ids": [str(people["other"].id)]}, format="json"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert rename(people["other"], workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_not_enforced_when_the_rule_is_off(self, workspace, project, people, assigned):
        Project.objects.filter(pk=project.pk).update(is_assignee_edit_rule_enabled=False)
        assert rename(people["other"], workspace, project, assigned).status_code == status.HTTP_204_NO_CONTENT

    def test_reading_is_not_restricted(self, workspace, project, people, assigned):
        assert client_for(people["other"]).get(url(workspace, project, assigned)).status_code == status.HTTP_200_OK

    def test_discussion_stays_open(self, workspace, project, people, assigned):
        response = client_for(people["other"]).post(
            url(workspace, project, assigned, "comments/"), {"comment_html": "<p>hello</p>"}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED, response.content

    def test_a_rule_in_another_project_does_not_reach_this_one(self, workspace, project, create_user, people):
        other_project = Project.objects.create(
            name="Free", identifier="FRE", workspace=workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=other_project, member=people["other"], role=MEMBER, is_active=True)
        issue = Issue.objects.create(name="Elsewhere", workspace=workspace, project=other_project)
        IssueAssignee.objects.create(
            issue=issue, assignee=people["assignee"], project=other_project, workspace=workspace
        )

        assert rename(people["other"], workspace, other_project, issue).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.contract
@pytest.mark.django_db
class TestOtherWaysOfChangingIt:
    def test_deleting_is_refused_to_a_creator_who_is_not_assigned(self, workspace, project, people):
        issue = Issue.objects.create(name="Mine", workspace=workspace, project=project, created_by=people["other"])
        IssueAssignee.objects.create(issue=issue, assignee=people["assignee"], project=project, workspace=workspace)

        response = client_for(people["other"]).delete(url(workspace, project, issue))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Issue.objects.filter(pk=issue.pk).exists()

    def test_links(self, workspace, project, people, assigned):
        endpoint = url(workspace, project, assigned, "issue-links/")
        payload = {"url": "https://example.com"}

        assert client_for(people["other"]).post(endpoint, payload, format="json").status_code == 403
        assert client_for(people["assignee"]).post(endpoint, payload, format="json").status_code == 201

    def test_relations_from_the_work_item_page(self, workspace, project, people, assigned):
        partner = Issue.objects.create(name="Partner", workspace=workspace, project=project)
        payload = {"relation_type": "relates_to", "issues": [str(partner.id)]}
        endpoint = url(workspace, project, assigned, "issue-relation/")

        assert client_for(people["other"]).post(endpoint, payload, format="json").status_code == 403
        assert client_for(people["assignee"]).post(endpoint, payload, format="json").status_code == 201
        assert (
            client_for(people["other"])
            .post(
                url(workspace, project, assigned, "remove-relation/"),
                {"relation_type": "relates_to", "related_issue": str(partner.id)},
                format="json",
            )
            .status_code
            == 403
        )
        assert IssueRelation.objects.count() == 1

    def test_sub_items_need_the_right_on_the_parent_and_on_each_child(self, workspace, project, people, assigned):
        free_child = Issue.objects.create(name="Free child", workspace=workspace, project=project)
        locked_child = Issue.objects.create(name="Locked child", workspace=workspace, project=project)
        IssueAssignee.objects.create(issue=locked_child, assignee=people["lead"], project=project, workspace=workspace)
        endpoint = url(workspace, project, assigned, "sub-issues/")

        # the other member may not change the parent
        assert (
            client_for(people["other"])
            .post(endpoint, {"sub_issue_ids": [str(free_child.id)]}, format="json")
            .status_code
            == 403
        )
        # the assignee of the parent may not re-parent an item assigned to somebody else
        assert (
            client_for(people["assignee"])
            .post(endpoint, {"sub_issue_ids": [str(locked_child.id)]}, format="json")
            .status_code
            == 403
        )
        assert (
            client_for(people["assignee"])
            .post(endpoint, {"sub_issue_ids": [str(free_child.id)]}, format="json")
            .status_code
            == 200
        )

    def test_the_timeline_drag(self, workspace, project, people, assigned):
        endpoint = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-dates/"
        update = {"updates": [{"id": str(assigned.id), "start_date": "2026-01-05", "target_date": "2026-01-09"}]}

        assert client_for(people["other"]).post(endpoint, update, format="json").status_code == 403
        assert client_for(people["assignee"]).post(endpoint, update, format="json").status_code == 200

    def test_archiving_one_and_many(self, workspace, project, people, assigned):
        from plane.db.models import State

        done = State.objects.create(name="Done", project=project, workspace=workspace, group="completed")
        Issue.objects.filter(pk=assigned.pk).update(state=done)
        one = url(workspace, project, assigned, "archive/")
        many = f"/api/workspaces/{workspace.slug}/projects/{project.id}/bulk-archive-issues/"

        assert client_for(people["other"]).post(one).status_code == 403
        assert (
            client_for(people["other"]).post(many, {"issue_ids": [str(assigned.id)]}, format="json").status_code == 403
        )
        assert client_for(people["assignee"]).post(one).status_code == 200


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApi:
    def token_client(self, user):
        token = APIToken.objects.create(user=user, label="t", token=f"token-{user.id.hex}")
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        return client

    def test_patching_a_work_item(self, workspace, project, people, assigned):
        endpoint = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{assigned.id}/"

        refused = self.token_client(people["other"]).patch(endpoint, {"name": "Nope"}, format="json")
        allowed = self.token_client(people["assignee"]).patch(endpoint, {"name": "Fine"}, format="json")

        assert refused.status_code == status.HTTP_403_FORBIDDEN
        assert allowed.status_code == status.HTTP_200_OK, allowed.data

    def test_adding_a_relation(self, workspace, project, people, assigned):
        partner = Issue.objects.create(name="Partner", workspace=workspace, project=project)
        endpoint = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{assigned.id}/relations/"
        payload = {"relation_type": "relates_to", "issues": [str(partner.id)]}

        assert self.token_client(people["other"]).post(endpoint, payload, format="json").status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestRescheduleRespectsTheRule:
    def test_dependents_the_person_may_not_change_are_not_offered(self, workspace, project, people):
        mover = Issue.objects.create(
            name="Mover",
            workspace=workspace,
            project=project,
            start_date=date(2026, 1, 1),
            target_date=date(2026, 1, 10),
        )
        locked = Issue.objects.create(
            name="Locked",
            workspace=workspace,
            project=project,
            start_date=date(2026, 1, 11),
            target_date=date(2026, 1, 20),
        )
        IssueAssignee.objects.create(issue=locked, assignee=people["lead"], project=project, workspace=workspace)
        IssueRelation.objects.create(
            issue=locked, related_issue=mover, relation_type="blocked_by", project=project, workspace=workspace
        )
        # the other member owns the mover but not the dependent
        IssueAssignee.objects.create(issue=mover, assignee=people["other"], project=project, workspace=workspace)

        with mock.patch("plane.utils.issue_reschedule.issue_activity.delay"):
            response = client_for(people["other"]).patch(
                url(workspace, project, mover), {"target_date": "2026-01-14"}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        code = response.json()["error_code"]
        assert (code[0] if isinstance(code, list) else code) == "relation_date_conflict"
