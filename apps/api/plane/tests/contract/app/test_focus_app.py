# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The focus lists (D9): next, blocked, waiting on us, to approve and overdue, for the person who asks."""

import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from plane.db.models import (
    GroupKind,
    Issue,
    IssueAssignee,
    IssueGroupAssignee,
    IssueRaci,
    IssueRelation,
    Project,
    ProjectMember,
    State,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceFeature,
    WorkspaceMember,
)

ADMIN, MEMBER, GUEST = 20, 15, 5
TODAY = datetime.datetime.now(datetime.UTC).date()
YESTERDAY = TODAY - datetime.timedelta(days=1)
LATER = TODAY + datetime.timedelta(days=10)


def _project(workspace, user, name, identifier, **extra):
    project = Project.objects.create(name=name, identifier=identifier, workspace=workspace, created_by=user, **extra)
    ProjectMember.objects.create(project=project, member=user, role=ADMIN, is_active=True)
    for group, state_name in (
        ("backlog", "Backlog"),
        ("unstarted", "Todo"),
        ("started", "Doing"),
        ("completed", "Done"),
        ("cancelled", "Dropped"),
    ):
        State.objects.create(
            name=state_name,
            group=group,
            color="#fff",
            project=project,
            workspace=workspace,
            default=group == "unstarted",
        )
    return project


@pytest.fixture
def project(db, workspace, create_user):
    return _project(workspace, create_user, "Focus", "FOC")


def _issue(project, name, group="unstarted", assignees=(), created_by=None, **dates):
    issue = Issue.objects.create(
        name=name,
        project=project,
        workspace=project.workspace,
        state=State.objects.get(project=project, group=group),
        **dates,
    )
    if created_by is not None:
        # BaseModel.save() sets created_by from the request user (none in a test), so it is set afterwards
        Issue.objects.filter(pk=issue.pk).update(created_by=created_by)
    for user in assignees:
        IssueAssignee.objects.create(issue=issue, assignee=user, project=project, workspace=project.workspace)
    return issue


def _relate(issue, relation_type, related_issue):
    """Store ``issue <relation_type> related_issue`` the way the API does."""
    IssueRelation.objects.create(
        issue=issue,
        related_issue=related_issue,
        relation_type=relation_type,
        project=issue.project,
        workspace=issue.workspace,
    )


def _person(workspace, project, email, role=MEMBER):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _focus(client, workspace, project=None, **params):
    url = (
        f"/api/workspaces/{workspace.slug}/projects/{project.id}/focus/"
        if project
        else f"/api/workspaces/{workspace.slug}/focus/"
    )
    response = client.get(url, params)
    assert response.status_code == 200, response.data
    return response.data


def _names(section):
    return [item["name"] for item in section["items"]]


@pytest.fixture
def other(workspace, project):
    return _person(workspace, project, "other@focus.test")


@pytest.mark.contract
@pytest.mark.django_db
class TestNextAndBlocked:
    def test_startable_work_items_come_first_then_by_start_and_finish(
        self, session_client, workspace, project, create_user, other
    ):
        me = create_user
        later = _issue(project, "Later", assignees=[me], start_date=LATER)
        undated = _issue(project, "Undated", assignees=[me])
        soon = _issue(project, "Soon", assignees=[me], start_date=TODAY, finish_date=LATER)
        held = _issue(project, "Held", assignees=[me], start_date=YESTERDAY)
        _relate(held, "blocked_by", _issue(project, "Theirs", assignees=[other]))
        _issue(project, "Done", group="completed", assignees=[me], start_date=YESTERDAY)
        _issue(project, "Not mine", assignees=[other], start_date=YESTERDAY)

        data = _focus(session_client, workspace)

        assert _names(data["next"]) == ["Soon", "Later", "Undated", "Held"]
        assert data["next"]["count"] == 4
        startable = {item["name"]: item["startable"] for item in data["next"]["items"]}
        assert startable == {"Soon": True, "Later": True, "Undated": True, "Held": False}
        assert {later.id, undated.id, soon.id} <= {item["id"] for item in data["next"]["items"]}

    def test_blocked_lists_the_predecessors_and_who_holds_them(
        self, session_client, workspace, project, create_user, other
    ):
        me = create_user
        mine = _issue(project, "Mine", assignees=[me])
        theirs = _issue(project, "Theirs", assignees=[other], finish_date=LATER)
        _relate(mine, "blocked_by", theirs)

        data = _focus(session_client, workspace)

        assert _names(data["blocked"]) == ["Mine"]
        (entry,) = data["blocked"]["items"][0]["blocked_by"]
        assert entry["relation_type"] == "blocked_by" and entry["holds"] == "start"
        assert entry["issue"]["id"] == theirs.id
        assert entry["issue"]["assignee_ids"] == [other.id]
        assert entry["issue"]["finish_date"] == LATER
        assert entry["issue"]["project_identifier"] == "FOC"
        assert data["blocked"]["items"][0]["hidden_blocked_by_count"] == 0

    def test_each_relation_type_holds_up_until_its_predecessor_is_far_enough(
        self, session_client, workspace, project, create_user, other
    ):
        me = create_user
        cases = {
            # name: (stored relation, predecessor state, held up?, what is held)
            "FS open": ("blocked_by", "started", True, "start"),
            "FS done": ("blocked_by", "completed", False, None),
            "FS cancelled": ("blocked_by", "cancelled", False, None),
            "SS not started": ("start_before", "backlog", True, "start"),
            "SS started": ("start_before", "started", False, None),
            "FF open": ("finish_before", "started", True, "finish"),
            "FF done": ("finish_before", "completed", False, None),
            "SF not started": ("start_before_finish", "unstarted", True, "finish"),
            "SF started": ("start_before_finish", "started", False, None),
            "relates to": ("relates_to", "unstarted", False, None),
        }
        for name, (relation_type, predecessor_group, _, _) in cases.items():
            item = _issue(project, name, assignees=[me])
            predecessor = _issue(project, f"{name} (predecessor)", group=predecessor_group, assignees=[other])
            if relation_type == "blocked_by":
                _relate(item, relation_type, predecessor)
            else:
                # the other timeline relations are stored with the predecessor first
                _relate(predecessor, relation_type, item)

        data = _focus(session_client, workspace)

        blocked = {item["name"]: item for item in data["blocked"]["items"]}
        startable = {item["name"]: item["startable"] for item in data["next"]["items"]}
        for name, (_, _, is_held, holds) in cases.items():
            assert (name in blocked) is is_held, name
            if is_held:
                assert [entry["holds"] for entry in blocked[name]["blocked_by"]] == [holds], name
            # a work item held up only in its finish can still be started
            assert startable[name] is (holds != "start"), name
        seen_as = {name: item["blocked_by"][0]["relation_type"] for name, item in blocked.items()}
        assert seen_as == {
            "FS open": "blocked_by",
            "SS not started": "start_after",
            "FF open": "finish_after",
            "SF not started": "finish_after_start",
        }

    def test_work_assigned_to_my_group_is_mine(self, session_client, workspace, project, create_user):
        team = UserGroup.objects.create(workspace=workspace, name="Packaging")
        squad = UserGroup.objects.create(workspace=workspace, name="Artwork", parent=team)
        UserGroupMember.objects.create(workspace=workspace, group=squad, user=create_user)
        item = _issue(project, "Team work")
        IssueGroupAssignee.objects.create(issue=item, group=team, project=project, workspace=workspace)
        _issue(project, "Nobody's")

        data = _focus(session_client, workspace)

        assert _names(data["next"]) == ["Team work"]
        assert data["next"]["items"][0]["group_assignee_ids"] == [team.id]


@pytest.mark.contract
@pytest.mark.django_db
class TestWaitingOnUs:
    def test_other_peoples_work_held_up_by_mine(self, session_client, workspace, project, create_user, other):
        me = create_user
        mine = _issue(project, "Mine", assignees=[me])
        waits = _issue(project, "Waits", assignees=[other])
        _relate(waits, "blocked_by", mine)
        # held up by somebody else's work: not waiting on me
        _relate(_issue(project, "Waits elsewhere", assignees=[other]), "blocked_by", _issue(project, "Third"))
        # my work that is done holds nothing up
        done = _issue(project, "My done", group="completed", assignees=[me])
        _relate(_issue(project, "Free", assignees=[other]), "blocked_by", done)
        # my own work held up by my work is not somebody else's
        _relate(_issue(project, "Mine too", assignees=[me]), "blocked_by", mine)

        data = _focus(session_client, workspace)

        assert _names(data["waiting_on_us"]) == ["Waits"]
        (entry,) = data["waiting_on_us"]["items"][0]["waiting_on"]
        assert entry["issue"]["id"] == mine.id and entry["holds"] == "start"


@pytest.fixture
def raci_on(workspace, project):
    WorkspaceFeature.objects.create(workspace=workspace, key="raci", is_enabled=True)
    Project.objects.filter(pk=project.pk).update(is_raci_enabled=True)


def _department(workspace, name, code, members=()):
    group = UserGroup.objects.create(workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT)
    for user in members:
        UserGroupMember.objects.create(workspace=workspace, group=group, user=user)
    return group


def _role(issue, group, role):
    IssueRaci.objects.create(issue=issue, group=group, role=role, project=issue.project, workspace=issue.workspace)


@pytest.mark.contract
@pytest.mark.django_db
class TestToApprove:
    def test_work_items_my_departments_approve(self, session_client, workspace, project, create_user, raci_on):
        quality = _department(workspace, "Quality", "QA", members=[create_user])
        # several departments per person are not allowed today (#508); the lists take them all anyway
        legal = _department(workspace, "Legal", "LE", members=[create_user])
        marketing = _department(workspace, "Marketing", "RM")
        _role(_issue(project, "Label"), quality, "approver")
        _role(_issue(project, "Contract"), legal, "approver")
        _role(_issue(project, "Leaflet"), marketing, "approver")
        _role(_issue(project, "Consulted only"), quality, "consulted")
        _role(_issue(project, "Approved already", group="completed"), quality, "approver")

        data = _focus(session_client, workspace)

        assert sorted(_names(data["to_approve"])) == ["Contract", "Label"]
        assert data["raci_enabled"] is True
        assert sorted(data["department_ids"]) == sorted([str(quality.id), str(legal.id)])
        by_name = {item["name"]: item for item in data["to_approve"]["items"]}
        assert by_name["Label"]["approver_department_ids"] == [str(quality.id)]

    def test_nothing_while_raci_is_off(self, session_client, workspace, project, create_user, raci_on):
        quality = _department(workspace, "Quality", "QA", members=[create_user])
        _role(_issue(project, "Label"), quality, "approver")
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)

        assert _focus(session_client, workspace)["to_approve"]["count"] == 0

        Project.objects.filter(pk=project.pk).update(is_raci_enabled=True)
        WorkspaceFeature.objects.filter(workspace=workspace, key="raci").update(is_enabled=False)
        data = _focus(session_client, workspace)
        assert data["to_approve"]["count"] == 0 and data["raci_enabled"] is False

    def test_nothing_without_a_department(self, session_client, workspace, project, create_user, raci_on):
        _role(_issue(project, "Label"), _department(workspace, "Quality", "QA"), "approver")

        data = _focus(session_client, workspace)

        assert data["to_approve"] == {"count": 0, "items": []} and data["department_ids"] == []


@pytest.mark.contract
@pytest.mark.django_db
class TestOverdue:
    def test_due_date_or_planned_finish_passed(self, session_client, workspace, project, create_user, other):
        me = create_user
        _issue(project, "Late", assignees=[me], target_date=YESTERDAY, finish_date=YESTERDAY)
        _issue(project, "Due passed", assignees=[me], target_date=YESTERDAY, finish_date=LATER)
        _issue(project, "Finish passed", assignees=[me], finish_date=YESTERDAY, target_date=LATER)
        _issue(project, "Due today", assignees=[me], target_date=TODAY)
        _issue(project, "Done late", group="completed", assignees=[me], target_date=YESTERDAY)
        _issue(project, "Not mine", assignees=[other], target_date=YESTERDAY)

        data = _focus(session_client, workspace)

        reasons = {item["name"]: item["overdue"] for item in data["overdue"]["items"]}
        assert reasons == {"Late": ["due", "finish"], "Due passed": ["due"], "Finish passed": ["finish"]}
        assert data["today"] == TODAY


@pytest.mark.contract
@pytest.mark.django_db
class TestVisibilityAndScope:
    def test_a_guest_sees_only_what_they_created(self, workspace, project, create_user, other):
        guest = _person(workspace, project, "guest@focus.test", role=GUEST)
        own = _issue(project, "Own", assignees=[guest], created_by=guest)
        _issue(project, "Someone else's", assignees=[guest], created_by=other)
        _relate(own, "blocked_by", _issue(project, "Hidden predecessor", assignees=[other], created_by=other))

        data = _focus(_client(guest), workspace)

        assert _names(data["next"]) == ["Own"]
        (blocked,) = data["blocked"]["items"]
        assert blocked["blocked_by"] == [] and blocked["hidden_blocked_by_count"] == 1

        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        data = _focus(_client(guest), workspace)
        assert sorted(_names(data["next"])) == ["Own", "Someone else's"]
        assert data["blocked"]["items"][0]["hidden_blocked_by_count"] == 0

    def test_projects_i_am_not_in_do_not_count(self, session_client, workspace, project, create_user):
        elsewhere = Project.objects.create(name="Elsewhere", identifier="ELS", workspace=workspace)
        State.objects.create(name="Todo", group="unstarted", color="#fff", project=elsewhere, workspace=workspace)
        _issue(elsewhere, "Not my project", assignees=[create_user])
        _issue(project, "Mine", assignees=[create_user])

        assert _names(_focus(session_client, workspace)["next"]) == ["Mine"]

    def test_one_project_only(self, session_client, workspace, project, create_user, other):
        second = _project(workspace, create_user, "Second", "SEC")
        _issue(project, "First", assignees=[create_user])
        _issue(second, "Second", assignees=[create_user])
        predecessor = _issue(second, "Predecessor elsewhere", assignees=[other])
        _relate(_issue(project, "Held", assignees=[create_user]), "blocked_by", predecessor)

        data = _focus(session_client, workspace, project)

        assert sorted(_names(data["next"])) == ["First", "Held"]
        # a predecessor in another project still shows
        assert data["blocked"]["items"][0]["blocked_by"][0]["issue"]["id"] == predecessor.id

    def test_not_a_member_of_the_workspace(self, workspace, project):
        stranger = User.objects.create(email="stranger@focus.test", username="stranger@focus.test")

        response = _client(stranger).get(f"/api/workspaces/{workspace.slug}/focus/")

        assert response.status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestLimitsAndQueries:
    def test_limit_cuts_the_items_not_the_count(self, session_client, workspace, project, create_user):
        for index in range(4):
            _issue(project, f"Item {index}", assignees=[create_user])

        data = _focus(session_client, workspace, limit=2)

        assert data["next"]["count"] == 4 and len(data["next"]["items"]) == 2

    def _scenario(self, workspace, project, me, other, raci_department, size):
        for index in range(size):
            mine = _issue(project, f"Mine {index}", assignees=[me], target_date=YESTERDAY)
            theirs = _issue(project, f"Theirs {index}", assignees=[other])
            _relate(mine, "blocked_by", theirs)
            _relate(_issue(project, f"Waits {index}", assignees=[other]), "blocked_by", mine)
            _role(_issue(project, f"Approve {index}"), raci_department, "approver")

    def test_the_number_of_queries_does_not_grow_with_the_work_items(
        self, session_client, workspace, project, create_user, other, raci_on
    ):
        quality = _department(workspace, "Quality", "QA", members=[create_user])
        self._scenario(workspace, project, create_user, other, quality, 2)
        with CaptureQueriesContext(connection) as few:
            small = _focus(session_client, workspace)

        self._scenario(workspace, project, create_user, other, quality, 10)
        with CaptureQueriesContext(connection) as many:
            large = _focus(session_client, workspace)

        assert small["blocked"]["count"] == 2 and large["blocked"]["count"] == 12
        assert large["waiting_on_us"]["count"] == 12 and large["to_approve"]["count"] == 12
        assert len(many.captured_queries) == len(few.captured_queries)
        assert len(few.captured_queries) <= 30
