# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The inbox tabs: "Subscribed" lists what the person follows without being assigned to or having created it."""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, IssueAssignee, IssueSubscriber, Notification, Project, ProjectMember, WorkspaceMember
from plane.tests.factories import UserFactory


def notification_for(workspace, project, receiver, issue):
    return Notification.objects.create(
        workspace=workspace,
        project=project,
        receiver=receiver,
        triggered_by=receiver,
        entity_name="issue",
        entity_identifier=issue.id,
        sender="in_app:issue_activities:subscribed",
        title="updated",
        data={"issue": {"id": str(issue.id)}, "issue_activity": {"id": str(uuid4()), "field": "name"}},
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestSubscribedTab:
    @pytest.fixture
    def setup(self, workspace, create_user):
        project = Project.objects.create(name="Tabs", identifier="TAB", workspace=workspace, created_by=create_user)
        person = UserFactory()
        WorkspaceMember.objects.create(workspace=workspace, member=person, role=15)
        ProjectMember.objects.create(project=project, member=person, role=15, workspace=workspace, is_active=True)
        assigned = Issue.objects.create(name="Assigned", workspace=workspace, project=project, created_by=create_user)
        followed = Issue.objects.create(name="Followed", workspace=workspace, project=project, created_by=create_user)
        IssueAssignee.objects.create(issue=assigned, assignee=person, project=project, workspace=workspace)
        for issue in (assigned, followed):
            # assigning subscribes, and the person follows the other one
            IssueSubscriber.objects.create(issue=issue, subscriber=person, project=project, workspace=workspace)
        return {
            "person": person,
            "assigned": notification_for(workspace, project, person, assigned),
            "followed": notification_for(workspace, project, person, followed),
        }

    def listing(self, person, workspace, tab):
        client = APIClient()
        client.force_authenticate(user=person)
        response = client.get(f"/api/workspaces/{workspace.slug}/users/notifications/?type={tab}")
        assert response.status_code == status.HTTP_200_OK
        return {entry["id"] for entry in response.json()}

    def test_an_assigned_item_is_not_listed_as_merely_subscribed(self, workspace, setup):
        assert self.listing(setup["person"], workspace, "subscribed") == {str(setup["followed"].id)}

    def test_it_is_listed_under_assigned(self, workspace, setup):
        assert self.listing(setup["person"], workspace, "assigned") == {str(setup["assigned"].id)}
