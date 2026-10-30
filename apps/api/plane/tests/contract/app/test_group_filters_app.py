# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Filtering work items, modules and cycles by user group, and who may filter by which group."""

import json
import uuid

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Cycle,
    CycleIssue,
    Issue,
    IssueGroupAssignee,
    Module,
    ModuleMember,
    Project,
    ProjectGroup,
    ProjectMember,
    State,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceMember,
)

ADMIN, MEMBER, GUEST = 20, 15, 5


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Filters", identifier="FLT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


def _person(workspace, project, email, role=MEMBER):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _join(group, user):
    UserGroupMember.objects.create(workspace=group.workspace, group=group, user=user)


@pytest.fixture
def tree(workspace):
    sales = _group(workspace, "Sales")
    poland = _group(workspace, "Poland", parent=sales)
    support = _group(workspace, "Support")
    return {"sales": sales, "poland": poland, "support": support}


@pytest.fixture
def issues(workspace, project, tree):
    state = State.objects.get(project=project)
    made = {}
    for name, group in (("A", tree["sales"]), ("B", tree["poland"]), ("C", tree["support"]), ("D", None)):
        made[name] = Issue.objects.create(name=name, project=project, workspace=workspace, state=state)
        if group is not None:
            IssueGroupAssignee.objects.create(issue=made[name], group=group, project=project, workspace=workspace)
    return made


def _names(response):
    assert response.status_code == 200, response.data
    return sorted(row["name"] for row in response.data["results"])


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkItemsByGroup:
    def _url(self, workspace, project):
        return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"

    def _legacy(self, client, workspace, project, value):
        return _names(client.get(self._url(workspace, project), {"group_assignees": value}))

    def _rich(self, client, workspace, project, values):
        return _names(
            client.get(
                self._url(workspace, project), {"filters": json.dumps({"group_assignee_id__in": ",".join(values)})}
            )
        )

    def test_a_group_matches_the_work_items_of_the_groups_below_it(
        self, session_client, workspace, project, tree, issues
    ):
        assert self._legacy(session_client, workspace, project, str(tree["sales"].id)) == ["A", "B"]
        assert self._legacy(session_client, workspace, project, str(tree["poland"].id)) == ["B"]
        assert self._rich(session_client, workspace, project, [str(tree["sales"].id)]) == ["A", "B"]

    def test_none_finds_the_work_items_without_a_group_and_values_are_or_ed(
        self, session_client, workspace, project, tree, issues
    ):
        assert self._legacy(session_client, workspace, project, "none") == ["D"]
        assert self._legacy(session_client, workspace, project, f"none,{tree['support'].id}") == ["C", "D"]
        assert self._rich(session_client, workspace, project, ["none", str(tree["support"].id)]) == ["C", "D"]

    def test_my_groups_means_the_groups_of_the_person_and_the_ones_above_them(self, workspace, project, tree, issues):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)
        client = _client(person)

        # Poland and Sales, exactly: not the groups below them, not Support
        assert self._legacy(client, workspace, project, "my_groups") == ["A", "B"]
        assert self._rich(client, workspace, project, ["my_groups"]) == ["A", "B"]

    def test_an_admin_without_groups_finds_nothing_with_my_groups(self, session_client, workspace, project, issues):
        assert self._legacy(session_client, workspace, project, "my_groups") == []

    def test_somebody_else_may_only_use_the_groups_they_belong_to(self, workspace, project, tree, issues):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)
        client = _client(person)

        # Sales is above their group, so it is allowed; Support is not and is dropped
        assert self._legacy(client, workspace, project, f"{tree['sales'].id},{tree['support'].id}") == ["A", "B"]
        assert self._rich(client, workspace, project, [str(tree["support"].id), "none"]) == ["D"]

    def test_asking_only_for_groups_one_may_not_use_finds_nothing(self, workspace, project, tree, issues):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)
        client = _client(person)

        assert self._legacy(client, workspace, project, str(tree["support"].id)) == []
        assert self._rich(client, workspace, project, [str(tree["support"].id), str(uuid.uuid4())]) == []

    def test_a_group_of_another_workspace_is_never_used(self, session_client, workspace, project, issues, create_user):
        from plane.db.models import Workspace

        other = Workspace.objects.create(name="Other", owner=create_user, slug="other-ws")
        foreign = _group(other, "Foreign")

        assert self._legacy(session_client, workspace, project, str(foreign.id)) == []

    def test_a_person_in_no_group_filters_by_none_only(self, workspace, project, tree, issues):
        person = _person(workspace, project, "nobody@example.com")
        client = _client(person)

        assert self._legacy(client, workspace, project, "my_groups") == []
        assert self._legacy(client, workspace, project, "none") == ["D"]


@pytest.mark.contract
@pytest.mark.django_db
class TestModulesAndCyclesByGroup:
    def _modules(self, workspace, project, tree, admin):
        pl = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], pl)
        su = _person(workspace, project, "su@example.com")
        _join(tree["support"], su)
        by_lead = Module.objects.create(name="LeadPL", project=project, workspace=workspace, lead=pl)
        by_member = Module.objects.create(name="MemberSU", project=project, workspace=workspace)
        ModuleMember.objects.create(module=by_member, member=su, project=project, workspace=workspace)
        nobody = Module.objects.create(name="Nobody", project=project, workspace=workspace, lead=admin)
        return {"lead": by_lead, "member": by_member, "nobody": nobody}, pl

    def _module_names(self, client, workspace, project, groups=None):
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/modules/"
        response = client.get(url, {"groups": groups} if groups is not None else {})
        assert response.status_code == 200, response.data
        return sorted(row["name"] for row in response.data)

    def test_modules_are_filtered_by_the_groups_of_their_lead_and_members(
        self, session_client, workspace, project, tree, create_user
    ):
        self._modules(workspace, project, tree, create_user)

        # Sales counts the people of the groups below it
        assert self._module_names(session_client, workspace, project, str(tree["sales"].id)) == ["LeadPL"]
        assert self._module_names(session_client, workspace, project, str(tree["support"].id)) == ["MemberSU"]
        assert self._module_names(session_client, workspace, project, "none") == ["Nobody"]
        assert self._module_names(session_client, workspace, project, f"none,{tree['support'].id}") == [
            "MemberSU",
            "Nobody",
        ]

    def test_a_member_filters_modules_by_my_groups_and_only_by_their_own_groups(
        self, workspace, project, tree, create_user
    ):
        _, pl = self._modules(workspace, project, tree, create_user)
        client = _client(pl)

        assert self._module_names(client, workspace, project, "my_groups") == ["LeadPL"]
        assert self._module_names(client, workspace, project, str(tree["support"].id)) == []

    def test_every_module_carries_the_facts_the_web_filters_on(
        self, session_client, workspace, project, tree, create_user
    ):
        self._modules(workspace, project, tree, create_user)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/modules/"

        rows = {row["name"]: row for row in session_client.get(url).data}

        assert sorted(rows["LeadPL"]["group_ids"]) == sorted([str(tree["poland"].id), str(tree["sales"].id)])
        assert rows["LeadPL"]["has_group"] is True
        assert rows["Nobody"]["group_ids"] == []
        assert rows["Nobody"]["has_group"] is False
        assert rows["Nobody"]["in_my_groups"] is False

    def test_cycles_are_filtered_by_the_groups_of_their_work_items(
        self, session_client, workspace, project, tree, issues, create_user
    ):
        for name, issue_names in (("CPL", ["B"]), ("CSU", ["C"]), ("CNone", ["D"])):
            cycle = Cycle.objects.create(name=name, project=project, workspace=workspace, owned_by=create_user)
            for issue_name in issue_names:
                CycleIssue.objects.create(cycle=cycle, issue=issues[issue_name], project=project, workspace=workspace)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/cycles/"

        def names(groups):
            response = session_client.get(url, {"groups": groups})
            assert response.status_code == 200, response.data
            return sorted(row["name"] for row in response.data)

        assert names(str(tree["sales"].id)) == ["CPL"]  # a work item of Poland is on Sales
        assert names(str(tree["poland"].id)) == ["CPL"]
        assert names(str(tree["support"].id)) == ["CSU"]
        assert names("none") == ["CNone"]
        assert names(f"none,{tree['support'].id}") == ["CNone", "CSU"]

    def test_cycles_my_groups_is_exact_and_a_stranger_gets_nothing_for_foreign_groups(
        self, workspace, project, tree, issues, create_user
    ):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)
        for name, issue_name in (("CPL", "B"), ("CSU", "C")):
            cycle = Cycle.objects.create(name=name, project=project, workspace=workspace, owned_by=create_user)
            CycleIssue.objects.create(cycle=cycle, issue=issues[issue_name], project=project, workspace=workspace)
        client = _client(person)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/cycles/"

        mine = client.get(url, {"groups": "my_groups"})
        foreign = client.get(url, {"groups": str(tree["support"].id)})

        assert [row["name"] for row in mine.data] == ["CPL"]
        assert foreign.data == []


@pytest.mark.contract
@pytest.mark.django_db
class TestFilterableGroups:
    def _url(self, workspace):
        return f"/api/workspaces/{workspace.slug}/user-groups/filterable/"

    def test_an_admin_may_filter_by_every_group(self, session_client, workspace, tree):
        response = session_client.get(self._url(workspace))

        assert response.status_code == 200
        assert [row["name"] for row in response.data] == ["Poland", "Sales", "Support"]
        by_name = {row["name"]: row for row in response.data}
        assert str(by_name["Poland"]["parent_id"]) == str(tree["sales"].id)
        assert not any(row["is_member"] for row in response.data)

    def test_a_member_gets_their_groups_and_the_ones_above_them(self, workspace, project, tree):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)

        response = _client(person).get(self._url(workspace))

        assert response.status_code == 200
        assert [row["name"] for row in response.data] == ["Poland", "Sales"]
        assert all(row["is_member"] for row in response.data)

    def test_a_guest_may_ask_and_gets_only_their_groups(self, workspace, project, tree):
        guest = _person(workspace, project, "guest@example.com", role=GUEST)
        _join(tree["support"], guest)

        response = _client(guest).get(self._url(workspace))

        assert response.status_code == 200
        assert [row["name"] for row in response.data] == ["Support"]

    def test_somebody_outside_the_workspace_is_refused(self, workspace, tree):
        stranger = User.objects.create(email="x@example.com", username="x@example.com")

        assert _client(stranger).get(self._url(workspace)).status_code in (401, 403)


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectGroupFilter:
    def _url(self, workspace):
        return f"/api/workspaces/{workspace.slug}/projects/details/"

    @pytest.fixture
    def projects(self, workspace, create_user, tree):
        made = {}
        for name, identifier, group in (
            ("Sales project", "SAL", tree["sales"]),
            ("Poland project", "POL", tree["poland"]),
            ("Support project", "SUP", tree["support"]),
            ("Loose project", "LSE", None),
        ):
            project = Project.objects.create(
                name=name, identifier=identifier, workspace=workspace, created_by=create_user, network=2
            )
            ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
            if group is not None:
                ProjectGroup.objects.create(project=project, group=group, workspace=workspace)
            made[name] = project
        return made

    def _names(self, client, workspace, groups=None):
        response = client.get(self._url(workspace), {"groups": groups} if groups is not None else {})
        assert response.status_code == 200
        return sorted(row["name"] for row in response.data)

    def test_a_group_matches_the_projects_of_that_group_and_of_the_groups_above_it(
        self, session_client, workspace, tree, projects
    ):
        # Poland is below Sales: the Sales project is its parent's project, so Poland people find it too
        assert self._names(session_client, workspace, str(tree["poland"].id)) == ["Poland project", "Sales project"]
        assert self._names(session_client, workspace, str(tree["sales"].id)) == ["Sales project"]

    def test_none_finds_the_projects_without_a_project_group_and_values_are_or_ed(
        self, session_client, workspace, tree, projects
    ):
        assert self._names(session_client, workspace, "none") == ["Loose project"]
        assert self._names(session_client, workspace, f"none,{tree['support'].id}") == [
            "Loose project",
            "Support project",
        ]

    def test_my_groups_means_the_project_groups_among_the_groups_of_the_person(
        self, workspace, project, tree, projects
    ):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)

        # Poland and Sales are the person's groups; the Support and loose projects do not match
        assert self._names(_client(person), workspace, "my_groups") == ["Poland project", "Sales project"]

    def test_somebody_else_may_only_use_their_own_groups_and_gets_nothing_for_foreign_ones(
        self, workspace, project, tree, projects
    ):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)
        client = _client(person)

        assert self._names(client, workspace, f"{tree['sales'].id},{tree['support'].id}") == ["Sales project"]
        assert self._names(client, workspace, str(tree["support"].id)) == []
        # "Filters" is the plain project of the shared fixture: it has no project group either
        assert self._names(client, workspace, f"{tree['support'].id},none") == ["Filters", "Loose project"]

    def test_every_project_carries_the_facts_the_web_filters_on(
        self, session_client, workspace, project, tree, projects
    ):
        rows = {row["name"]: row for row in session_client.get(self._url(workspace)).data}

        assert set(rows["Sales project"]["group_ids"]) == {str(tree["sales"].id), str(tree["poland"].id)}
        assert rows["Sales project"]["has_group"] is True
        assert rows["Poland project"]["group_ids"] == [str(tree["poland"].id)]
        assert rows["Loose project"]["group_ids"] == []
        assert rows["Loose project"]["has_group"] is False
        assert rows["Loose project"]["in_my_groups"] is False

    def test_group_ids_are_limited_to_the_groups_the_person_may_filter_by(self, workspace, project, tree, projects):
        person = _person(workspace, project, "pl@example.com")
        _join(tree["poland"], person)

        rows = {row["name"]: row for row in _client(person).get(self._url(workspace)).data}

        assert set(rows["Sales project"]["group_ids"]) == {str(tree["sales"].id), str(tree["poland"].id)}
        assert rows["Sales project"]["in_my_groups"] is True
        # Support is not one of their groups: it is not named, but the project still has a group
        assert rows["Support project"]["group_ids"] == []
        assert rows["Support project"]["has_group"] is True
        assert rows["Support project"]["in_my_groups"] is False
