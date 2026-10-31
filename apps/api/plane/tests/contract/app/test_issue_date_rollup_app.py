# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The dates rolled up from the work items below a parent, for the timeline."""

from datetime import date
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, Project, ProjectMember, User, WorkspaceMember

URL = "/api/workspaces/{slug}/projects/{project_id}/issue-date-rollups/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Rollups", identifier="RU", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


def make_issue(project, workspace, author, name, parent=None, start=None, end=None, due=None):
    issue = Issue(
        name=name,
        project=project,
        workspace=workspace,
        parent=parent,
        start_date=date.fromisoformat(start) if start else None,
        finish_date=date.fromisoformat(end) if end else None,
        target_date=date.fromisoformat(due) if due else None,
    )
    issue.save(created_by_id=author.id)
    return issue


def user_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def get(client, workspace, project, ids):
    return client.get(URL.format(slug=workspace.slug, project_id=project.id), {"issue_ids": ",".join(map(str, ids))})


@pytest.mark.contract
@pytest.mark.django_db
class TestIssueDateRollup:
    @pytest.fixture
    def tree(self, project, workspace, create_user):
        parent = make_issue(project, workspace, create_user, "Parent", start="2026-02-01", end="2026-02-10")
        child = make_issue(project, workspace, create_user, "Child", parent, "2026-02-05", "2026-02-20")
        grandchild = make_issue(project, workspace, create_user, "Grandchild", child, "2026-01-15", "2026-01-31")
        leaf = make_issue(project, workspace, create_user, "Leaf")
        return parent, child, grandchild, leaf

    def test_rolls_up_over_every_level_and_leaves_out_work_items_without_children(
        self, session_client, workspace, project, tree
    ):
        parent, child, grandchild, leaf = tree
        response = get(session_client, workspace, project, [parent.id, child.id, grandchild.id, leaf.id])
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            str(parent.id): {
                "start_date": "2026-01-15",
                "target_date": "2026-02-20",
                "children_count": 1,
                "descendants_count": 2,
            },
            str(child.id): {
                "start_date": "2026-01-15",
                "target_date": "2026-01-31",
                "children_count": 1,
                "descendants_count": 1,
            },
        }

    def test_archived_and_deleted_work_items_do_not_count(self, session_client, workspace, project, tree):
        parent, child, grandchild, _ = tree
        Issue.objects.filter(pk=grandchild.pk).update(archived_at=timezone.now())
        body = get(session_client, workspace, project, [parent.id]).json()
        assert body[str(parent.id)]["start_date"] == "2026-02-05"
        assert body[str(parent.id)]["descendants_count"] == 1
        Issue.objects.filter(pk=child.pk).update(deleted_at=timezone.now())
        assert get(session_client, workspace, project, [parent.id]).json() == {}

    def test_the_end_is_the_finish_date_not_the_due_date(self, session_client, workspace, project, create_user):
        parent = make_issue(project, workspace, create_user, "Parent")
        make_issue(project, workspace, create_user, "Child", parent, "2026-04-01", "2026-04-10", due="2026-09-30")
        make_issue(project, workspace, create_user, "Due only", parent, due="2026-12-31")
        body = get(session_client, workspace, project, [parent.id]).json()
        assert (body[str(parent.id)]["start_date"], body[str(parent.id)]["target_date"]) == ("2026-04-01", "2026-04-10")

    def test_empty_and_malformed_requests(self, session_client, workspace, project):
        assert get(session_client, workspace, project, []).json() == {}
        assert get(session_client, workspace, project, ["not-an-id"]).status_code == status.HTTP_400_BAD_REQUEST
        too_many = [uuid4() for _ in range(501)]
        assert get(session_client, workspace, project, too_many).status_code == status.HTTP_400_BAD_REQUEST

    def test_ids_of_another_project_are_left_out(self, session_client, workspace, project, create_user):
        other = Project.objects.create(name="Other", identifier="OT", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=other, member=create_user, workspace=workspace, role=20)
        parent = make_issue(other, workspace, create_user, "P")
        make_issue(other, workspace, create_user, "C", parent, "2026-01-01", "2026-01-02")
        assert get(session_client, workspace, project, [parent.id]).json() == {}

    def test_a_non_member_is_refused(self, workspace, project, tree):
        stranger = User.objects.create(email=f"s-{uuid4().hex[:6]}@plane.so", username=f"s_{uuid4().hex[:6]}")
        WorkspaceMember.objects.create(workspace=workspace, member=stranger, role=15)
        response = get(user_client(stranger), workspace, project, [tree[0].id])
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_a_guest_only_gets_dates_from_their_own_work_items(self, workspace, project, create_user):
        guest = User.objects.create(email=f"g-{uuid4().hex[:6]}@plane.so", username=f"g_{uuid4().hex[:6]}")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
        ProjectMember.objects.create(project=project, member=guest, workspace=workspace, role=5)
        parent = make_issue(project, workspace, guest, "Mine", start="2026-03-01", end="2026-03-05")
        make_issue(project, workspace, guest, "Mine too", parent, "2026-03-02", "2026-03-04")
        make_issue(project, workspace, create_user, "Not mine", parent, "2026-06-01", "2026-06-30")
        body = get(user_client(guest), workspace, project, [parent.id]).json()
        assert body[str(parent.id)]["target_date"] == "2026-03-04"
        assert body[str(parent.id)]["descendants_count"] == 1
        # a project that lets guests see everything shows all of it
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        body = get(user_client(guest), workspace, project, [parent.id]).json()
        assert body[str(parent.id)]["target_date"] == "2026-06-30"
