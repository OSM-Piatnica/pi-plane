# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Initiatives and goals of a workspace: who manages them, what links are accepted, and what progress a person gets.

Admins and members of the workspace manage them, guests have no access. Work item numbers come only from the
projects the requester is a member of; the others are counted as hidden and never named.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Initiative,
    InitiativeEpic,
    InitiativeProject,
    InitiativeUpdate,
    Issue,
    IssueType,
    Project,
    ProjectMember,
    State,
    User,
    Workspace,
    WorkspaceMember,
)

SLUG = "test-workspace"
INITIATIVES = f"/api/workspaces/{SLUG}/initiatives/"
ADMIN, MEMBER, GUEST = 20, 15, 5


def _url(initiative_id, suffix=""):
    return f"{INITIATIVES}{initiative_id}/{suffix}"


def _person(workspace, label, role=MEMBER):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"{label}-{unique}@plane.so", username=f"{label}_{unique}", first_name=label)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _as(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _project(workspace, identifier, members=()):
    project = Project.objects.create(name=f"{identifier} project", identifier=identifier, workspace=workspace)
    for user in members:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=MEMBER)
    return project


def _issues(project, group, number, issue_type=None):
    state, _ = State.objects.get_or_create(
        project=project, workspace=project.workspace, group=group, defaults={"name": group}
    )
    return [
        Issue.objects.create(
            name=f"{group} {index}", project=project, workspace=project.workspace, state=state, type=issue_type
        )
        for index in range(number)
    ]


def _create(client, **data):
    return client.post(INITIATIVES, {"name": "Thing", **data}, format="json")


@pytest.fixture
def epic_type(db, workspace):
    return IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeCrud:
    def test_create_read_update_and_delete(self, session_client, workspace, create_user):
        created = _create(
            session_client,
            name="  Launch  ",
            description_html="<p>Why</p>",
            lead=str(create_user.id),
            start_date="2026-01-01",
            target_date="2026-06-30",
            color="#ff0000",
            logo_props={"in_use": "emoji"},
        )

        assert created.status_code == 201, created.data
        assert created.data["name"] == "Launch"
        assert created.data["kind"] == "initiative"
        assert created.data["status"] == "planned"
        assert created.data["health"] is None
        assert created.data["progress"]["total_issues"] == 0
        assert created.data["progress_is_partial"] is False
        assert created.data["project_ids"] == [] and created.data["epic_ids"] == []

        url = _url(created.data["id"])
        assert session_client.get(url).data["name"] == "Launch"
        updated = session_client.patch(url, {"status": "active", "health": "on_track"}, format="json")
        assert updated.status_code == 200
        assert (updated.data["status"], updated.data["health"]) == ("active", "on_track")

        assert session_client.delete(url).status_code == 204
        assert session_client.get(url).status_code == 404
        assert not Initiative.objects.filter(workspace=workspace).exists()

    def test_a_goal_has_no_parent_and_an_initiative_only_a_goal_of_the_workspace(
        self, session_client, workspace, create_user
    ):
        goal = _create(session_client, name="Goal", kind="goal").data
        initiative = _create(session_client, name="Work", parent=goal["id"])
        other = Workspace.objects.create(name="Other", slug="other-workspace", owner=create_user)
        foreign_goal = Initiative.objects.create(workspace=other, name="Theirs", kind="goal")

        assert initiative.status_code == 201
        assert str(initiative.data["parent"]) == str(goal["id"])
        assert _create(session_client, kind="goal", parent=goal["id"]).status_code == 400
        assert _create(session_client, parent=initiative.data["id"]).status_code == 400
        assert _create(session_client, parent=str(foreign_goal.id)).status_code == 400
        assert session_client.patch(_url(goal["id"]), {"parent": goal["id"]}, format="json").status_code == 400

    def test_the_kind_cannot_be_changed(self, session_client, workspace):
        initiative = _create(session_client).data

        response = session_client.patch(_url(initiative["id"]), {"kind": "goal"}, format="json")

        assert response.status_code == 400

    def test_dates_must_be_in_order_also_when_only_one_is_changed(self, session_client, workspace):
        assert _create(session_client, start_date="2026-03-02", target_date="2026-03-01").status_code == 400
        initiative = _create(session_client, start_date="2026-03-01", target_date="2026-03-31").data

        response = session_client.patch(_url(initiative["id"]), {"target_date": "2026-02-01"}, format="json")

        assert response.status_code == 400

    def test_a_name_is_required_and_the_choices_are_checked(self, session_client, workspace):
        assert _create(session_client, name="   ").status_code == 400
        assert _create(session_client, kind="programme").status_code == 400
        assert _create(session_client, status="done").status_code == 400
        assert _create(session_client, health="fine").status_code == 400

    def test_the_lead_must_be_a_member_of_the_workspace(self, session_client, workspace):
        stranger = User.objects.create(email="stranger@plane.so", username="stranger")

        assert _create(session_client, lead=str(stranger.id)).status_code == 400

    def test_the_description_is_sanitised(self, session_client, workspace):
        created = _create(session_client, description_html="<p>Fine</p><script>alert(1)</script>")

        assert created.status_code == 201
        assert "<script" not in created.data["description_html"]
        assert "<p>Fine</p>" in created.data["description_html"]

    def test_deleting_a_goal_keeps_its_initiatives(self, session_client, workspace):
        goal = _create(session_client, name="Goal", kind="goal").data
        initiative = _create(session_client, parent=goal["id"]).data

        assert session_client.delete(_url(goal["id"])).status_code == 204

        kept = session_client.get(_url(initiative["id"]))
        assert kept.status_code == 200
        assert kept.data["parent"] is None

    def test_an_initiative_of_another_workspace_is_not_found(self, session_client, workspace, create_user):
        other = Workspace.objects.create(name="Other", slug="other-workspace", owner=create_user)
        theirs = Initiative.objects.create(workspace=other, name="Theirs")

        assert session_client.get(_url(theirs.id)).status_code == 404
        assert session_client.patch(_url(theirs.id), {"name": "Mine"}, format="json").status_code == 404
        assert session_client.delete(_url(theirs.id)).status_code == 404


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeListFilters:
    def test_filter_by_kind_status_parent_and_project(self, session_client, workspace, create_user):
        project = _project(workspace, "FIL", [create_user])
        goal = _create(session_client, name="Goal", kind="goal").data
        _create(session_client, name="Under", parent=goal["id"], status="active")
        loose = _create(session_client, name="Loose", status="paused").data
        session_client.post(_url(loose["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")

        def names(query):
            response = session_client.get(f"{INITIATIVES}?{query}")
            assert response.status_code == 200, response.data
            return {row["name"] for row in response.data}

        assert names("") == {"Goal", "Under", "Loose"}
        assert names("kind=goal") == {"Goal"}
        assert names("kind=initiative") == {"Under", "Loose"}
        assert names("status=active,paused") == {"Under", "Loose"}
        assert names("status=paused") == {"Loose"}
        assert names(f"parent={goal['id']}") == {"Under"}
        assert names("kind=initiative&parent=none") == {"Loose"}
        assert names(f"project={project.id}") == {"Loose"}

    def test_bad_filter_values_are_refused(self, session_client, workspace):
        for query in ("kind=programme", "status=done", "parent=abc", "project=abc"):
            assert session_client.get(f"{INITIATIVES}?{query}").status_code == 400

    def test_the_project_filter_matches_nothing_for_a_project_the_person_is_not_in(
        self, session_client, workspace, create_user
    ):
        outsider = _person(workspace, "outsider")
        project = _project(workspace, "SEC", [create_user])
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")

        response = _as(outsider).get(f"{INITIATIVES}?project={project.id}")

        assert response.status_code == 200
        assert response.data == []


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeLinks:
    def test_projects_are_added_once_and_removed(self, session_client, workspace, create_user):
        first = _project(workspace, "ONE", [create_user])
        second = _project(workspace, "TWO", [create_user])
        initiative = _create(session_client).data
        projects_url = _url(initiative["id"], "projects/")

        added = session_client.post(projects_url, {"project_ids": [str(first.id), str(second.id)]}, format="json")
        again = session_client.post(projects_url, {"project_ids": [str(first.id)]}, format="json")

        assert added.status_code == 200 and again.status_code == 200
        assert {str(value) for value in again.data["project_ids"]} == {str(first.id), str(second.id)}
        assert InitiativeProject.objects.filter(initiative_id=initiative["id"]).count() == 2

        assert session_client.delete(f"{projects_url}{first.id}/").status_code == 204
        assert session_client.delete(f"{projects_url}{first.id}/").status_code == 404
        assert [str(value) for value in session_client.get(_url(initiative["id"])).data["project_ids"]] == [
            str(second.id)
        ]

    def test_a_removed_project_can_be_linked_again(self, session_client, workspace, create_user):
        project = _project(workspace, "ONE", [create_user])
        initiative = _create(session_client).data
        projects_url = _url(initiative["id"], "projects/")
        body = {"project_ids": [str(project.id)]}

        session_client.post(projects_url, body, format="json")
        session_client.delete(f"{projects_url}{project.id}/")
        again = session_client.post(projects_url, body, format="json")

        assert again.status_code == 200
        assert [str(value) for value in again.data["project_ids"]] == [str(project.id)]

    def test_a_project_of_another_workspace_or_one_the_person_is_not_in_is_refused(
        self, session_client, workspace, create_user
    ):
        other = Workspace.objects.create(name="Other", slug="other-workspace", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=ADMIN)
        foreign = _project(other, "FOR", [create_user])
        not_mine = _project(workspace, "NOT")
        initiative = _create(session_client).data
        projects_url = _url(initiative["id"], "projects/")

        for body in (
            {"project_ids": [str(foreign.id)]},
            {"project_ids": [str(not_mine.id)]},
            {"project_ids": [str(uuid4())]},
            {"project_ids": []},
            {"project_ids": ["abc"]},
            {"project_ids": str(not_mine.id)},
            {},
        ):
            assert session_client.post(projects_url, body, format="json").status_code == 400, body
        assert not InitiativeProject.objects.filter(initiative_id=initiative["id"]).exists()

    def test_a_goal_takes_no_projects_or_epics(self, session_client, workspace, create_user, epic_type):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        goal = _create(session_client, kind="goal").data

        projects = session_client.post(_url(goal["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        epics = session_client.post(_url(goal["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        assert projects.status_code == 400 and epics.status_code == 400

    def test_only_epics_of_the_persons_projects_are_linked(self, session_client, workspace, create_user, epic_type):
        project = _project(workspace, "ONE", [create_user])
        not_mine = _project(workspace, "NOT")
        epic = _issues(project, "started", 1, epic_type)[0]
        task = _issues(project, "started", 1)[0]
        hidden_epic = _issues(not_mine, "started", 1, epic_type)[0]
        initiative = _create(session_client).data
        epics_url = _url(initiative["id"], "epics/")

        assert session_client.post(epics_url, {"epic_ids": [str(task.id)]}, format="json").status_code == 400
        assert session_client.post(epics_url, {"epic_ids": [str(hidden_epic.id)]}, format="json").status_code == 400
        assert (
            session_client.post(epics_url, {"epic_ids": [str(epic.id), str(task.id)]}, format="json").status_code == 400
        )
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()

        added = session_client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")
        again = session_client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")

        assert added.status_code == 200 and again.status_code == 200
        assert [str(value) for value in again.data["epic_ids"]] == [str(epic.id)]
        assert InitiativeEpic.objects.filter(initiative_id=initiative["id"]).count() == 1
        assert session_client.delete(f"{epics_url}{epic.id}/").status_code == 204
        assert session_client.delete(f"{epics_url}{epic.id}/").status_code == 404

    def test_links_to_projects_the_person_is_not_in_cannot_be_removed_by_them(
        self, session_client, workspace, create_user, epic_type
    ):
        outsider = _person(workspace, "outsider")
        project = _project(workspace, "SEC", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        client = _as(outsider)

        assert client.delete(_url(initiative["id"], f"projects/{project.id}/")).status_code == 404
        assert client.delete(_url(initiative["id"], f"epics/{epic.id}/")).status_code == 404
        assert InitiativeProject.objects.filter(initiative_id=initiative["id"]).count() == 1
        assert InitiativeEpic.objects.filter(initiative_id=initiative["id"]).count() == 1


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeProgress:
    def test_progress_counts_work_items_by_state_group_without_epics(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        _issues(project, "backlog", 1)
        _issues(project, "started", 2)
        _issues(project, "completed", 3)
        _issues(project, "started", 1, epic_type)
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")

        detail = session_client.get(_url(initiative["id"])).data
        listed = session_client.get(INITIATIVES).data[0]

        expected = {"total_issues": 6, "backlog": 1, "unstarted": 0, "started": 2, "completed": 3, "cancelled": 0}
        assert detail["progress"] == expected
        assert listed["progress"] == expected

    def test_a_goal_adds_up_its_initiatives_and_counts_a_shared_project_once(
        self, session_client, workspace, create_user
    ):
        shared = _project(workspace, "SHA", [create_user])
        single = _project(workspace, "SIN", [create_user])
        _issues(shared, "started", 4)
        _issues(single, "completed", 1)
        goal = _create(session_client, name="Goal", kind="goal").data
        first = _create(session_client, name="First", parent=goal["id"]).data
        second = _create(session_client, name="Second", parent=goal["id"]).data
        session_client.post(_url(first["id"], "projects/"), {"project_ids": [str(shared.id)]}, format="json")
        session_client.post(
            _url(second["id"], "projects/"), {"project_ids": [str(shared.id), str(single.id)]}, format="json"
        )

        detail = session_client.get(_url(goal["id"])).data

        assert detail["progress"]["total_issues"] == 5
        assert detail["progress"]["started"] == 4
        assert {str(value) for value in detail["project_ids"]} == {str(shared.id), str(single.id)}
        assert {str(value) for value in detail["initiative_ids"]} == {str(first["id"]), str(second["id"])}

    def test_projects_the_person_is_not_in_are_left_out_and_not_named(
        self, session_client, workspace, create_user, epic_type
    ):
        outsider = _person(workspace, "outsider")
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        _issues(visible, "started", 1)
        _issues(secret, "completed", 9)
        secret_epic = _issues(secret, "started", 1, epic_type)[0]
        goal = _create(session_client, name="Goal", kind="goal").data
        initiative = _create(session_client, name="Work", parent=goal["id"]).data
        session_client.post(
            _url(initiative["id"], "projects/"), {"project_ids": [str(visible.id), str(secret.id)]}, format="json"
        )
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(secret_epic.id)]}, format="json")

        whole = session_client.get(_url(initiative["id"])).data
        client = _as(outsider)
        rows = {row["name"]: row for row in client.get(INITIATIVES).data}
        detail = client.get(_url(initiative["id"]))

        assert whole["progress"]["total_issues"] == 10
        assert whole["progress_is_partial"] is False and whole["hidden_project_count"] == 0
        for row in (rows["Goal"], rows["Work"], detail.data):
            assert row["progress"]["total_issues"] == 1
            assert row["progress"]["completed"] == 0
            assert row["progress_is_partial"] is True
            assert row["hidden_project_count"] == 1
            assert [str(value) for value in row["project_ids"]] == [str(visible.id)]
        assert detail.data["epic_ids"] == [] and detail.data["hidden_epic_count"] == 1
        body = detail.content.decode() + client.get(INITIATIVES).content.decode()
        assert str(secret.id) not in body
        assert secret.name not in body
        assert str(secret_epic.id) not in body


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeUpdates:
    def test_an_update_is_listed_and_sets_the_health(self, session_client, workspace, create_user):
        initiative = _create(session_client).data
        updates_url = _url(initiative["id"], "updates/")

        first = session_client.post(updates_url, {"health": "on_track", "text": "Going well"}, format="json")
        second = session_client.post(updates_url, {"health": "at_risk", "text": "Supplier is late"}, format="json")
        listed = session_client.get(updates_url)

        assert first.status_code == 201 and second.status_code == 201
        assert str(second.data["author"]) == str(create_user.id)
        assert [row["text"] for row in listed.data] == ["Supplier is late", "Going well"]
        assert session_client.get(_url(initiative["id"])).data["health"] == "at_risk"

    def test_an_update_needs_a_known_health(self, session_client, workspace):
        initiative = _create(session_client).data
        updates_url = _url(initiative["id"], "updates/")

        assert session_client.post(updates_url, {"text": "No health"}, format="json").status_code == 400
        assert session_client.post(updates_url, {"health": "fine"}, format="json").status_code == 400
        assert not InitiativeUpdate.objects.filter(initiative_id=initiative["id"]).exists()

    def test_the_author_cannot_be_chosen(self, session_client, workspace, create_user):
        other = _person(workspace, "other")
        initiative = _create(session_client).data

        response = session_client.post(
            _url(initiative["id"], "updates/"), {"health": "on_track", "author": str(other.id)}, format="json"
        )

        assert response.status_code == 201
        assert str(response.data["author"]) == str(create_user.id)


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeAccess:
    def test_a_member_manages_initiatives(self, workspace):
        member = _person(workspace, "member")
        client = _as(member)

        created = _create(client)

        assert created.status_code == 201
        assert client.patch(_url(created.data["id"]), {"name": "Renamed"}, format="json").status_code == 200
        assert (
            client.post(_url(created.data["id"], "updates/"), {"health": "on_track"}, format="json").status_code == 201
        )
        assert client.delete(_url(created.data["id"])).status_code == 204

    def test_a_guest_has_no_access(self, session_client, workspace):
        guest = _person(workspace, "guest", GUEST)
        initiative = _create(session_client).data
        client = _as(guest)

        assert client.get(INITIATIVES).status_code == 403
        assert _create(client).status_code == 403
        assert client.get(_url(initiative["id"])).status_code == 403
        assert client.patch(_url(initiative["id"]), {"name": "Mine"}, format="json").status_code == 403
        assert client.delete(_url(initiative["id"])).status_code == 403
        assert client.get(_url(initiative["id"], "updates/")).status_code == 403
        assert client.post(_url(initiative["id"], "projects/"), {"project_ids": []}, format="json").status_code == 403
        assert client.post(_url(initiative["id"], "epics/"), {"epic_ids": []}, format="json").status_code == 403

    def test_a_person_outside_the_workspace_and_an_anonymous_one_have_no_access(self, session_client, workspace):
        stranger = User.objects.create(email="stranger@plane.so", username="stranger")
        initiative = _create(session_client).data

        assert _as(stranger).get(INITIATIVES).status_code == 403
        assert _as(stranger).get(_url(initiative["id"])).status_code == 403
        assert APIClient().get(INITIATIVES).status_code in (401, 403)
