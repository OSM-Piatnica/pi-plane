# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI notifications and warnings: the workspace matrix, "who will be notified" and the project warnings."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    GroupKind,
    Issue,
    IssueRaci,
    IssueRelation,
    IssueType,
    Project,
    ProjectMember,
    RaciNotificationSetting,
    State,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceFeature,
    WorkspaceMember,
)

ADMIN, MEMBER, GUEST = 20, 15, 5


@pytest.fixture
def project(db, workspace, create_user):
    WorkspaceFeature.objects.create(workspace=workspace, key="raci", is_enabled=True)
    project = Project.objects.create(
        name="Raci", identifier="RCW", workspace=workspace, created_by=create_user, is_raci_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    State.objects.create(name="Done", group="completed", color="#fff", project=project, workspace=workspace)
    return project


def _issue(project, name, **extra):
    state = State.objects.get(project=project, name=extra.pop("state", "Todo"))
    return Issue.objects.create(name=name, project=project, workspace=project.workspace, state=state, **extra)


def _department(workspace, code, *people, **extra):
    group = UserGroup.objects.create(workspace=workspace, name=code, code=code, kind=GroupKind.DEPARTMENT, **extra)
    for user in people:
        UserGroupMember.objects.create(workspace=workspace, group=group, user=user)
    return group


def _give(issue, group, role):
    IssueRaci.objects.create(issue=issue, group=group, role=role, project=issue.project, workspace=issue.workspace)


def _person(workspace, email, project=None, role=MEMBER):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    if project is not None:
        ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _matrix_url(workspace):
    return f"/api/workspaces/{workspace.slug}/raci-notifications/"


@pytest.mark.contract
@pytest.mark.django_db
class TestMatrix:
    def test_defaults_until_changed(self, session_client, workspace):
        response = session_client.get(_matrix_url(workspace))

        assert response.status_code == 200
        assert response.data["events"][0] == "new_version"
        assert response.data["matrix"]["approval_requested"] == ["responsible", "approver"]
        assert response.data["matrix"] == response.data["defaults"]

    def test_an_admin_changes_some_events(self, session_client, workspace):
        response = session_client.patch(
            _matrix_url(workspace), {"matrix": {"comment": ["informed", "responsible"]}}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["matrix"]["comment"] == ["responsible", "informed"]
        assert response.data["matrix"]["new_version"] == ["responsible", "consulted"]
        assert RaciNotificationSetting.objects.get(workspace=workspace).matrix["comment"] == ["responsible", "informed"]

    def test_bad_matrix_is_refused(self, session_client, workspace):
        response = session_client.patch(_matrix_url(workspace), {"matrix": {"comment": ["boss"]}}, format="json")

        assert response.status_code == 400
        assert not RaciNotificationSetting.objects.filter(workspace=workspace).exists()

    def test_members_read_but_do_not_change(self, workspace):
        member = _person(workspace, "member@example.com")
        client = _client(member)

        assert client.get(_matrix_url(workspace)).status_code == 200
        assert client.patch(_matrix_url(workspace), {"matrix": {"comment": []}}, format="json").status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestPreview:
    def test_departments_and_people_per_event(self, session_client, workspace, project):
        resp = _person(workspace, "resp@example.com", project)
        outsider = _person(workspace, "out@example.com")
        appr = _person(workspace, "appr@example.com", project)
        rm = _department(workspace, "RM", resp, outsider)
        za = _department(workspace, "ZA", appr)
        issue = _issue(project, "Box")
        _give(issue, rm, "responsible")
        _give(issue, za, "approver")

        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/raci/notifications/"
        response = session_client.get(url)

        assert response.status_code == 200
        events = {entry["event"]: entry for entry in response.data["events"]}
        assert events["approval_requested"]["member_ids"] == sorted([str(resp.id), str(appr.id)])
        assert events["comment"]["departments"] == [{"group_id": str(rm.id), "role": "responsible", "member_count": 1}]

    def test_refused_while_raci_is_off(self, session_client, workspace, project):
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)
        issue = _issue(project, "Box")

        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/raci/notifications/"
        assert session_client.get(url).status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
class TestWarnings:
    def url(self, project):
        return f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/raci-warnings/"

    def test_warnings(self, session_client, workspace, project):
        resp = _person(workspace, "r@example.com", project)
        outside = _person(workspace, "o@example.com")
        rm = _department(workspace, "RM", resp)
        empty = _department(workspace, "EM")
        away = _department(workspace, "AW", outside)
        milestone_type = IssueType.objects.create(workspace=workspace, name="Milestone", kind="milestone")

        first = _issue(project, "First", start_date=date(2026, 1, 5), finish_date=date(2026, 1, 9))
        last = _issue(project, "Last", start_date=date(2026, 1, 12), finish_date=date(2026, 1, 16))
        loose = _issue(project, "Loose", start_date=date(2026, 1, 7), finish_date=date(2026, 1, 8))
        milestone = _issue(project, "Go-live", type=milestone_type, target_date=date(2026, 1, 20))
        done = _issue(project, "Done", state="Done")
        IssueRelation.objects.create(
            issue=last, related_issue=first, relation_type="blocked_by", project=project, workspace=workspace
        )
        for issue in (first, last, loose, milestone):
            _give(issue, rm, "responsible")
        _give(first, empty, "consulted")
        _give(last, away, "informed")

        response = session_client.get(self.url(project))

        assert response.status_code == 200, response.data
        items = {kind: [entry["id"] for entry in entries] for kind, entries in response.data["items"].items()}
        assert items["no_responsible"] == []  # the completed work item does not count
        assert str(done.id) not in sum(items.values(), [])
        assert items["milestone_without_approver"] == [str(milestone.id)]
        assert str(loose.id) in items["no_predecessor"] and str(first.id) not in items["no_predecessor"]
        assert str(loose.id) in items["no_successor"] and str(last.id) not in items["no_successor"]
        assert str(milestone.id) not in items["no_successor"]  # it has a due date
        reasons = {entry["group_id"]: entry["reason"] for entry in response.data["departments"]}
        assert reasons == {str(empty.id): "no_members", str(away.id): "no_project_members"}
        assert response.data["counts"]["department_without_members"] == 2

    def test_guests_and_raci_off(self, session_client, workspace, project):
        guest = _person(workspace, "g@example.com", project, role=GUEST)

        assert _client(guest).get(self.url(project)).status_code == 403
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)
        assert session_client.get(self.url(project)).status_code == 400
