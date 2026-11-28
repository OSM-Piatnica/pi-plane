# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Initiatives and goals of a workspace: who manages them, what links are accepted, and what progress a person gets.

Admins and members of the workspace manage them, guests have no access. Work item numbers come only from the
projects the requester is a member of; the others are counted as hidden and never named.

The endpoints answer only while the Initiatives feature is switched on, so every test here switches it on for the
test workspace first (``initiatives_on``); ``TestInitiativesSwitch`` switches it off again.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from plane.app.serializers.initiative import InitiativeSerializer
from plane.app.views.workspace.initiative import MAX_LINKS_PER_REQUEST
from plane.bgtasks.deletion_task import soft_delete_related_objects
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
    WorkspaceFeature,
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


@pytest.fixture(autouse=True)
def initiatives_on(db, workspace):
    WorkspaceFeature.objects.create(workspace=workspace, key="initiatives", is_enabled=True)


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
        updated = session_client.patch(url, {"status": "active"}, format="json")
        assert updated.status_code == 200
        assert updated.data["status"] == "active"

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
        member = _person(workspace, "member")
        WorkspaceMember.objects.create(workspace=other, member=member, role=ADMIN)
        ProjectMember.objects.create(workspace=other, project=foreign, member=member, role=ADMIN)
        client = _as(member)
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
            assert client.post(projects_url, body, format="json").status_code == 400, body
        assert not InitiativeProject.objects.filter(initiative_id=initiative["id"]).exists()

    def test_a_goal_takes_no_projects_or_epics(self, session_client, workspace, create_user, epic_type):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        goal = _create(session_client, kind="goal").data

        projects = session_client.post(_url(goal["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        epics = session_client.post(_url(goal["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        assert projects.status_code == 400 and epics.status_code == 400

    def test_only_epics_of_the_persons_projects_are_linked(self, session_client, workspace, create_user, epic_type):
        member = _person(workspace, "member")
        project = _project(workspace, "ONE", [create_user, member])
        not_mine = _project(workspace, "NOT")
        epic = _issues(project, "started", 1, epic_type)[0]
        task = _issues(project, "started", 1)[0]
        hidden_epic = _issues(not_mine, "started", 1, epic_type)[0]
        initiative = _create(session_client).data
        client = _as(member)
        epics_url = _url(initiative["id"], "epics/")

        assert client.post(epics_url, {"epic_ids": [str(task.id)]}, format="json").status_code == 400
        assert client.post(epics_url, {"epic_ids": [str(hidden_epic.id)]}, format="json").status_code == 400
        assert client.post(epics_url, {"epic_ids": [str(epic.id), str(task.id)]}, format="json").status_code == 400
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()

        added = client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")
        again = client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")

        assert added.status_code == 200 and again.status_code == 200
        assert [str(value) for value in again.data["epic_ids"]] == [str(epic.id)]
        assert InitiativeEpic.objects.filter(initiative_id=initiative["id"]).count() == 1
        assert client.delete(f"{epics_url}{epic.id}/").status_code == 204
        assert client.delete(f"{epics_url}{epic.id}/").status_code == 404

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

    def test_an_archived_project_is_not_linked_and_an_archived_epic_neither(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        archived = _project(workspace, "ARC", [create_user])
        archived_epic = _issues(project, "started", 1, epic_type)[0]
        Issue.objects.filter(pk=archived_epic.pk).update(archived_at=timezone.now().date())
        Project.objects.filter(pk=archived.pk).update(archived_at=timezone.now())
        initiative = _create(session_client).data

        projects = session_client.post(
            _url(initiative["id"], "projects/"), {"project_ids": [str(project.id), str(archived.id)]}, format="json"
        )
        epics = session_client.post(
            _url(initiative["id"], "epics/"), {"epic_ids": [str(archived_epic.id)]}, format="json"
        )

        assert projects.status_code == 400 and "archived" in projects.data["error"]
        assert epics.status_code == 400
        assert not InitiativeProject.objects.filter(initiative_id=initiative["id"]).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()

    def test_one_request_links_a_limited_number(self, session_client, workspace):
        initiative = _create(session_client).data
        too_many = [str(uuid4()) for _ in range(MAX_LINKS_PER_REQUEST + 1)]

        projects = session_client.post(_url(initiative["id"], "projects/"), {"project_ids": too_many}, format="json")
        epics = session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": too_many}, format="json")

        assert projects.status_code == 400 and str(MAX_LINKS_PER_REQUEST) in projects.data["error"]
        assert epics.status_code == 400 and str(MAX_LINKS_PER_REQUEST) in epics.data["error"]

    def test_an_epic_that_was_given_another_type_can_be_unlinked(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        initiative = _create(session_client).data
        epics_url = _url(initiative["id"], "epics/")
        session_client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")
        Issue.objects.filter(pk=epic.pk).update(type=IssueType.objects.create(workspace=workspace, name="Task"))

        shown = session_client.get(_url(initiative["id"])).data
        removed = session_client.delete(f"{epics_url}{epic.id}/")

        assert shown["epic_ids"] == [] and shown["hidden_epic_count"] == 0
        assert removed.status_code == 204
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()

    def test_deleting_an_initiative_with_a_retyped_epic_leaves_no_link(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        session_client.post(_url(initiative["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        Issue.objects.filter(pk=epic.pk).update(type=None)

        with patch("plane.db.mixins.soft_delete_related_objects.delay") as queued:
            response = session_client.delete(_url(initiative["id"]))
        # What the worker does with the queued task
        soft_delete_related_objects(*queued.call_args.args, **queued.call_args.kwargs)

        assert response.status_code == 204
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()
        assert not InitiativeProject.objects.filter(initiative_id=initiative["id"]).exists()

    def test_what_a_model_refuses_is_answered_with_its_message(self, session_client, workspace):
        refusal = ValidationError({"parent": "The parent of an initiative must be a goal."})

        with patch.object(InitiativeSerializer, "save", side_effect=refusal):
            response = _create(session_client)

        assert response.status_code == 400
        assert response.data == {"parent": ["The parent of an initiative must be a goal."]}


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeProjectGuests:
    """A workspace member can be a guest of a single project: there they see less and link nothing."""

    def _setup(self, session_client, workspace, create_user, epic_type, guests_see_all):
        project = _project(workspace, "GUE", [create_user])
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=guests_see_all)
        _issues(project, "started", 3)
        epic = _issues(project, "started", 1, epic_type)[0]
        guest = _person(workspace, "projectguest")
        ProjectMember.objects.create(workspace=workspace, project=project, member=guest, role=GUEST)
        linked = _create(session_client, name="Linked").data
        empty = _create(session_client, name="Empty").data
        session_client.post(_url(linked["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        session_client.post(_url(linked["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        return project, epic, _as(guest), linked, empty

    def test_a_guest_who_sees_only_their_own_work_items_gets_a_count_of_hidden_projects_only(
        self, session_client, workspace, create_user, epic_type
    ):
        project, epic, client, linked, empty = self._setup(session_client, workspace, create_user, epic_type, False)

        detail = client.get(_url(linked["id"]))

        assert detail.data["progress"]["total_issues"] == 0
        assert detail.data["progress_is_partial"] is True and detail.data["hidden_project_count"] == 1
        assert detail.data["project_ids"] == [] and detail.data["epic_ids"] == []
        assert detail.data["hidden_epic_count"] == 1
        assert str(project.id) not in detail.content.decode() and str(epic.id) not in detail.content.decode()
        assert client.get(f"{INITIATIVES}?project={project.id}").data == []

    def test_a_guest_who_sees_only_their_own_work_items_links_and_unlinks_nothing(
        self, session_client, workspace, create_user, epic_type
    ):
        project, epic, client, linked, empty = self._setup(session_client, workspace, create_user, epic_type, False)

        add_project = client.post(_url(empty["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        add_epic = client.post(_url(empty["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        drop_project = client.delete(_url(linked["id"], f"projects/{project.id}/"))
        drop_epic = client.delete(_url(linked["id"], f"epics/{epic.id}/"))

        assert add_project.status_code == 400 and add_epic.status_code == 400
        assert drop_project.status_code == 404 and drop_epic.status_code == 404
        assert not InitiativeProject.objects.filter(initiative_id=empty["id"]).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=empty["id"]).exists()
        assert InitiativeProject.objects.filter(initiative_id=linked["id"]).count() == 1
        assert InitiativeEpic.objects.filter(initiative_id=linked["id"]).count() == 1

    def test_a_guest_of_a_project_that_shows_everything_sees_the_progress_but_links_and_unlinks_nothing(
        self, session_client, workspace, create_user, epic_type
    ):
        project, epic, client, linked, empty = self._setup(session_client, workspace, create_user, epic_type, True)

        detail = client.get(_url(linked["id"])).data
        add_project = client.post(_url(empty["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        add_epic = client.post(_url(empty["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        drop_project = client.delete(_url(linked["id"], f"projects/{project.id}/"))
        drop_epic = client.delete(_url(linked["id"], f"epics/{epic.id}/"))

        assert detail["progress"]["total_issues"] == 3
        assert detail["progress_is_partial"] is False
        assert [str(value) for value in detail["project_ids"]] == [str(project.id)]
        assert [str(value) for value in detail["epic_ids"]] == [str(epic.id)]
        assert add_project.status_code == 403 and add_epic.status_code == 403
        assert drop_project.status_code == 403 and drop_epic.status_code == 403
        assert not InitiativeProject.objects.filter(initiative_id=empty["id"]).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=empty["id"]).exists()
        assert InitiativeProject.objects.filter(initiative_id=linked["id"]).count() == 1
        assert InitiativeEpic.objects.filter(initiative_id=linked["id"]).count() == 1

    def test_a_workspace_admin_who_is_not_in_the_project_sees_links_and_unlinks_everything(
        self, session_client, workspace, create_user, epic_type
    ):
        owner = _person(workspace, "owner")
        project = _project(workspace, "ONE", [owner])
        _issues(project, "started", 4)
        epic = _issues(project, "backlog", 1, epic_type)[0]
        goal = _create(session_client, name="Goal", kind="goal").data
        initiative = _create(session_client, name="Work", parent=goal["id"]).data
        projects_url, epics_url = _url(initiative["id"], "projects/"), _url(initiative["id"], "epics/")

        add_project = session_client.post(projects_url, {"project_ids": [str(project.id)]}, format="json")
        add_epic = session_client.post(epics_url, {"epic_ids": [str(epic.id)]}, format="json")
        rows = {row["name"]: row for row in session_client.get(INITIATIVES).data}

        assert not ProjectMember.objects.filter(project=project, member=create_user).exists()
        assert add_project.status_code == 200 and add_epic.status_code == 200
        for row in (rows["Goal"], rows["Work"], session_client.get(_url(goal["id"])).data):
            assert row["progress"]["total_issues"] == 4
            assert row["progress_is_partial"] is False and row["hidden_project_count"] == 0
            assert [str(value) for value in row["project_ids"]] == [str(project.id)]
            assert [str(value) for value in row["epic_ids"]] == [str(epic.id)]
            assert row["hidden_epic_count"] == 0
        assert session_client.delete(f"{projects_url}{project.id}/").status_code == 204
        assert session_client.delete(f"{epics_url}{epic.id}/").status_code == 204
        assert not InitiativeProject.objects.filter(initiative_id=initiative["id"]).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=initiative["id"]).exists()

    def test_a_workspace_admin_does_not_link_an_archived_project_they_are_not_in(self, session_client, workspace):
        archived = _project(workspace, "ARC")
        Project.objects.filter(pk=archived.pk).update(archived_at=timezone.now())
        initiative = _create(session_client).data

        response = session_client.post(
            _url(initiative["id"], "projects/"), {"project_ids": [str(archived.id)]}, format="json"
        )

        assert response.status_code == 400 and "archived" in response.data["error"]

    def test_a_plain_member_who_is_not_in_the_project_sees_a_hidden_count_and_links_nothing(
        self, session_client, workspace, create_user, epic_type
    ):
        owner = _person(workspace, "owner")
        project = _project(workspace, "ONE", [owner])
        _issues(project, "started", 4)
        epic = _issues(project, "backlog", 1, epic_type)[0]
        goal = _create(session_client, name="Goal", kind="goal").data
        linked = _create(session_client, name="Linked", parent=goal["id"]).data
        empty = _create(session_client, name="Empty").data
        session_client.post(_url(linked["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        session_client.post(_url(linked["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        client = _as(_person(workspace, "plain"))

        add_project = client.post(_url(empty["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        add_epic = client.post(_url(empty["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")
        drop_project = client.delete(_url(linked["id"], f"projects/{project.id}/"))
        drop_epic = client.delete(_url(linked["id"], f"epics/{epic.id}/"))

        for row in (client.get(_url(linked["id"])).data, client.get(_url(goal["id"])).data):
            assert row["progress"]["total_issues"] == 0
            assert row["progress_is_partial"] is True and row["hidden_project_count"] == 1
            assert row["project_ids"] == [] and row["epic_ids"] == []
            assert row["hidden_epic_count"] == 1
        assert add_project.status_code == 400 and add_epic.status_code == 400
        assert drop_project.status_code == 404 and drop_epic.status_code == 404
        assert InitiativeProject.objects.filter(initiative_id=linked["id"]).count() == 1
        assert InitiativeEpic.objects.filter(initiative_id=linked["id"]).count() == 1
        assert not InitiativeProject.objects.filter(initiative_id=empty["id"]).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=empty["id"]).exists()


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

    def test_a_goal_lists_the_epics_of_its_initiatives_once_and_only_counts_the_hidden_ones(
        self, session_client, workspace, create_user, epic_type
    ):
        outsider = _person(workspace, "outsider")
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        shared = _issues(visible, "started", 1, epic_type)[0]
        secret_epic = _issues(secret, "started", 1, epic_type)[0]
        goal = _create(session_client, name="Goal", kind="goal").data
        first = _create(session_client, name="First", parent=goal["id"]).data
        second = _create(session_client, name="Second", parent=goal["id"]).data
        both = {"epic_ids": [str(shared.id), str(secret_epic.id)]}
        session_client.post(_url(first["id"], "epics/"), both, format="json")
        session_client.post(_url(second["id"], "epics/"), both, format="json")

        whole = session_client.get(_url(goal["id"])).data
        client = _as(outsider)
        detail = client.get(_url(goal["id"]))
        listed = {row["name"]: row for row in client.get(INITIATIVES).data}["Goal"]

        assert {str(value) for value in whole["epic_ids"]} == {str(shared.id), str(secret_epic.id)}
        assert len(whole["epic_ids"]) == 2 and whole["hidden_epic_count"] == 0
        for row in (detail.data, listed):
            assert [str(value) for value in row["epic_ids"]] == [str(shared.id)]
            assert row["hidden_epic_count"] == 1
        assert str(secret_epic.id) not in detail.content.decode()


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

    def test_the_health_is_set_only_by_an_update(self, session_client, workspace):
        created = _create(session_client, health="on_track")
        assert created.status_code == 201
        assert created.data["health"] is None

        url = _url(created.data["id"])
        session_client.post(_url(created.data["id"], "updates/"), {"health": "at_risk", "text": "Late"}, format="json")
        patched = session_client.patch(url, {"health": "off_track", "name": "Renamed"}, format="json")

        assert patched.status_code == 200
        assert (patched.data["name"], patched.data["health"]) == ("Renamed", "at_risk")
        assert Initiative.objects.get(pk=created.data["id"]).health == "at_risk"

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


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeDelete:
    """Every member edits; deleting is for a workspace admin, the lead and the person who made it."""

    def _made_by(self, user, **data):
        created = _create(_as(user), **data)
        assert created.status_code == 201, created.data
        return created.data

    def test_a_workspace_admin_deletes_what_somebody_else_made(self, session_client, workspace):
        initiative = self._made_by(_person(workspace, "maker"))

        assert session_client.delete(_url(initiative["id"])).status_code == 204

    def test_the_lead_deletes_it(self, workspace):
        lead = _person(workspace, "lead")
        initiative = self._made_by(_person(workspace, "maker"), lead=str(lead.id))

        assert _as(lead).delete(_url(initiative["id"])).status_code == 204

    def test_the_creator_deletes_it_also_when_somebody_else_leads_it(self, workspace):
        maker = _person(workspace, "maker")
        initiative = self._made_by(maker, kind="goal", lead=str(_person(workspace, "lead").id))

        assert _as(maker).delete(_url(initiative["id"])).status_code == 204

    def test_another_member_edits_but_does_not_delete(self, workspace):
        initiative = self._made_by(_person(workspace, "maker"))
        client = _as(_person(workspace, "other"))

        edited = client.patch(_url(initiative["id"]), {"name": "Renamed"}, format="json")
        deleted = client.delete(_url(initiative["id"]))

        assert edited.status_code == 200
        assert deleted.status_code == 403
        assert Initiative.objects.filter(pk=initiative["id"]).exists()

    def test_a_guest_does_not_delete_even_as_the_lead(self, workspace):
        guest = _person(workspace, "guest", GUEST)
        initiative = self._made_by(_person(workspace, "maker"), lead=str(guest.id))

        assert _as(guest).delete(_url(initiative["id"])).status_code == 403
        assert Initiative.objects.filter(pk=initiative["id"]).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativesSwitch:
    """A workspace admin switches the app on; until then the endpoints refuse everybody, admins included."""

    def _switch_off(self, workspace):
        WorkspaceFeature.objects.filter(workspace=workspace, key="initiatives").update(is_enabled=False)

    def test_nothing_answers_while_the_feature_is_off(self, session_client, workspace):
        initiative = Initiative.objects.create(workspace=workspace, name="Old")
        self._switch_off(workspace)

        for response in (
            session_client.get(INITIATIVES),
            _create(session_client),
            session_client.get(_url(initiative.id)),
            session_client.get(_url(initiative.id, "epics/")),
            session_client.get(_url(initiative.id, "epics/search/")),
            session_client.get(_url(initiative.id, "updates/")),
        ):
            assert response.status_code == 403
        assert Initiative.objects.filter(workspace=workspace).count() == 1

    def test_switching_it_on_opens_them(self, session_client, workspace):
        WorkspaceFeature.objects.filter(workspace=workspace, key="initiatives").delete()
        assert session_client.get(INITIATIVES).status_code == 403

        switched = session_client.patch(f"/api/workspaces/{SLUG}/features/", {"initiatives": True}, format="json")

        assert switched.status_code == 200
        assert session_client.get(INITIATIVES).status_code == 200
        self._switch_off(workspace)
        assert session_client.get(INITIATIVES).status_code == 403


def _child(epic, group, number=1, project=None):
    """Child work items of an Epic, in its project unless another is given."""
    project = project or epic.project
    state, _ = State.objects.get_or_create(
        project=project, workspace=project.workspace, group=group, defaults={"name": group}
    )
    return [
        Issue.objects.create(
            name=f"child {group} {index}",
            project=project,
            workspace=project.workspace,
            state=state,
            parent=epic,
        )
        for index in range(number)
    ]


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeEpicProgress:
    """The second figure: the child work items of the linked Epics, apart from the main one."""

    def test_the_epic_figure_counts_the_children_of_the_linked_epics_and_not_the_main_one(
        self, session_client, workspace, create_user, epic_type
    ):
        linked_project = _project(workspace, "ONE", [create_user])
        other_project = _project(workspace, "TWO", [create_user])
        _issues(linked_project, "started", 2)
        epic = _issues(other_project, "backlog", 1, epic_type)[0]
        _child(epic, "completed", 3)
        _child(epic, "started", 1)
        _issues(other_project, "started", 5)  # not a child: counted nowhere
        initiative = _create(session_client).data
        session_client.post(
            _url(initiative["id"], "projects/"), {"project_ids": [str(linked_project.id)]}, format="json"
        )
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        detail = session_client.get(_url(initiative["id"])).data
        listed = session_client.get(INITIATIVES).data[0]

        for row in (detail, listed):
            assert row["progress"]["total_issues"] == 2
            assert row["epic_progress"] == {
                "total_issues": 4,
                "backlog": 0,
                "unstarted": 0,
                "started": 1,
                "completed": 3,
                "cancelled": 0,
            }
            assert row["epic_progress_is_partial"] is False

    def test_an_epic_in_a_linked_project_counts_in_both_figures_once_each(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        _child(epic, "completed", 2)
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "projects/"), {"project_ids": [str(project.id)]}, format="json")
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        detail = session_client.get(_url(initiative["id"])).data

        # The Epic itself is in neither; its two children are in both, once in each
        assert detail["progress"]["total_issues"] == 2
        assert detail["epic_progress"]["total_issues"] == 2

    def test_hidden_epics_are_counted_not_listed_and_make_the_figure_partial(
        self, session_client, workspace, create_user, epic_type
    ):
        outsider = _person(workspace, "outsider")
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        open_epic = _issues(visible, "started", 1, epic_type)[0]
        secret_epic = _issues(secret, "started", 1, epic_type)[0]
        Issue.objects.filter(pk=secret_epic.pk).update(name="Secret Epic")
        _child(open_epic, "started", 1)
        _child(secret_epic, "completed", 6)
        initiative = _create(session_client).data
        session_client.post(
            _url(initiative["id"], "epics/"), {"epic_ids": [str(open_epic.id), str(secret_epic.id)]}, format="json"
        )

        whole = session_client.get(_url(initiative["id"])).data
        client = _as(outsider)
        detail = client.get(_url(initiative["id"]))
        epics = client.get(_url(initiative["id"], "epics/"))

        assert whole["epic_progress"]["total_issues"] == 7 and whole["epic_progress_is_partial"] is False
        assert detail.data["epic_progress"]["total_issues"] == 1
        assert detail.data["epic_progress"]["completed"] == 0
        assert detail.data["epic_progress_is_partial"] is True
        assert detail.data["hidden_epic_count"] == 1
        assert [str(row["id"]) for row in epics.data] == [str(open_epic.id)]
        body = detail.content.decode() + epics.content.decode()
        assert str(secret_epic.id) not in body and "Secret Epic" not in body

    def test_children_in_a_project_the_person_may_not_see_are_left_out(
        self, session_client, workspace, create_user, epic_type
    ):
        outsider = _person(workspace, "outsider")
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        epic = _issues(visible, "started", 1, epic_type)[0]
        _child(epic, "started", 1)
        _child(epic, "completed", 4, project=secret)
        initiative = _create(session_client).data
        session_client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        for_outsider = _as(outsider).get(_url(initiative["id"], "epics/")).data[0]
        whole = session_client.get(_url(initiative["id"], "epics/")).data[0]

        assert for_outsider["progress"]["total_issues"] == 1 and for_outsider["progress_is_partial"] is True
        assert whole["progress"]["total_issues"] == 5 and whole["progress_is_partial"] is False

    def test_a_goal_counts_an_epic_of_two_of_its_initiatives_once(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        epic = _issues(project, "started", 1, epic_type)[0]
        _child(epic, "started", 3)
        goal = _create(session_client, name="Goal", kind="goal").data
        for name in ("First", "Second"):
            child = _create(session_client, name=name, parent=goal["id"]).data
            session_client.post(_url(child["id"], "epics/"), {"epic_ids": [str(epic.id)]}, format="json")

        detail = session_client.get(_url(goal["id"])).data
        epics = session_client.get(_url(goal["id"], "epics/")).data

        assert detail["epic_progress"]["total_issues"] == 3
        assert [str(row["id"]) for row in epics] == [str(epic.id)]


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeEpicList:
    def test_the_linked_epics_come_with_their_project_state_and_progress(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        first, second = _issues(project, "started", 2, epic_type)
        _child(first, "completed", 1)
        _child(first, "backlog", 1)
        initiative = _create(session_client).data
        session_client.post(
            _url(initiative["id"], "epics/"), {"epic_ids": [str(first.id), str(second.id)]}, format="json"
        )

        response = session_client.get(_url(initiative["id"], "epics/"))

        assert response.status_code == 200
        assert [str(row["id"]) for row in response.data] == [str(first.id), str(second.id)]
        row = response.data[0]
        assert row["name"] == first.name
        assert row["sequence_id"] == first.sequence_id
        assert str(row["project_id"]) == str(project.id)
        assert row["project_identifier"] == "ONE"
        assert row["state_group"] == "started"
        assert row["progress"]["total_issues"] == 2 and row["progress"]["completed"] == 1
        assert row["progress_is_partial"] is False
        assert response.data[1]["progress"]["total_issues"] == 0

    def test_an_unknown_initiative_is_not_found(self, session_client, workspace):
        assert session_client.get(_url(uuid4(), "epics/")).status_code == 404


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeEpicSearch:
    def test_epics_the_person_may_link_are_found_by_name_or_number(
        self, session_client, workspace, create_user, epic_type
    ):
        project = _project(workspace, "ONE", [create_user])
        epic = Issue.objects.create(name="Packaging relaunch", project=project, workspace=workspace, type=epic_type)
        Issue.objects.create(name="Packaging task", project=project, workspace=workspace)  # not an Epic
        initiative = _create(session_client).data
        search = _url(initiative["id"], "epics/search/")

        by_name = session_client.get(search, {"search": "packag"}).data
        by_number = session_client.get(search, {"search": f"one-{epic.sequence_id}"}).data
        everything = session_client.get(search).data

        assert [str(row["id"]) for row in by_name] == [str(epic.id)]
        assert [str(row["id"]) for row in by_number] == [str(epic.id)]
        assert by_name[0]["project_identifier"] == "ONE"
        assert [str(row["id"]) for row in everything] == [str(epic.id)]

    def test_linked_epics_and_epics_of_projects_the_person_may_not_link_are_left_out(
        self, workspace, create_user, epic_type
    ):
        member = _person(workspace, "member")
        guest_project = _project(workspace, "GST")
        ProjectMember.objects.create(workspace=workspace, project=guest_project, member=member, role=GUEST)
        Project.objects.filter(pk=guest_project.pk).update(guest_view_all_features=True)
        own = _project(workspace, "OWN", [member])
        hidden = _project(workspace, "HID", [create_user])
        _issues(guest_project, "started", 1, epic_type)
        _issues(hidden, "started", 1, epic_type)
        linked, free = _issues(own, "started", 2, epic_type)
        client = _as(member)
        initiative = _create(client).data
        client.post(_url(initiative["id"], "epics/"), {"epic_ids": [str(linked.id)]}, format="json")

        found = client.get(_url(initiative["id"], "epics/search/")).data

        assert [str(row["id"]) for row in found] == [str(free.id)]

    def test_a_goal_has_no_epics_to_link(self, session_client, workspace):
        goal = _create(session_client, name="Goal", kind="goal").data

        assert session_client.get(_url(goal["id"], "epics/search/")).status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
class TestInitiativeDescriptionImages:
    ASSETS = f"/api/assets/v2/workspaces/{SLUG}/"

    def _upload(self, client):
        return client.post(
            self.ASSETS,
            {"name": "chart.png", "type": "image/png", "size": 100, "entity_type": "INITIATIVE_DESCRIPTION"},
            format="json",
        )

    def test_a_member_uploads_an_image_for_a_description(self, workspace):
        with patch("plane.app.views.asset.v2.get_storage") as storage:
            storage.return_value.generate_presigned_post.return_value = {"url": "https://storage.test/"}
            response = self._upload(_as(_person(workspace, "member")))

        assert response.status_code == 200, response.data
        assert response.data["asset_id"]

    def test_a_guest_does_not(self, workspace):
        response = self._upload(_as(_person(workspace, "guest", GUEST)))

        assert response.status_code == 403
