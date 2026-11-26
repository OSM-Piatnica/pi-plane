# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI on work items: the roles of departments, who may set them, where they show and what filters find."""

import json
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from plane.bgtasks.issue_activities_task import update_raci_activity
from plane.db.models import (
    GroupKind,
    Issue,
    IssueRaci,
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


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.app.views.issue.raci.issue_activity") as activity,
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
    ):
        yield activity


@pytest.fixture
def raci_on(workspace):
    WorkspaceFeature.objects.create(workspace=workspace, key="raci", is_enabled=True)


@pytest.fixture
def project(db, workspace, create_user, raci_on):
    project = Project.objects.create(
        name="Raci", identifier="RAC", workspace=workspace, created_by=create_user, is_raci_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


def _issue(project, name, parent=None, created_by=None):
    return Issue.objects.create(
        name=name,
        project=project,
        workspace=project.workspace,
        state=State.objects.get(project=project),
        parent=parent,
        created_by=created_by,
    )


@pytest.fixture
def issue(project):
    return _issue(project, "Packaging")


def _department(workspace, name, code, **extra):
    return UserGroup.objects.create(workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT, **extra)


@pytest.fixture
def departments(workspace):
    return {
        "rm": _department(workspace, "Marketing", "RM", color="#3f76ff", sort_order=1),
        "qa": _department(workspace, "Quality", "QA", sort_order=2),
        "pr": _department(workspace, "Production", "PR", sort_order=3),
    }


def _person(workspace, project, email, role=MEMBER):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _url(project, issue):
    return f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/{issue.id}/raci/"


def _body(*pairs):
    return {"raci": [{"group_id": str(group.id), "role": role} for group, role in pairs]}


def _roles(issue):
    return {
        str(group_id): role for group_id, role in IssueRaci.objects.filter(issue=issue).values_list("group_id", "role")
    }


@pytest.mark.contract
@pytest.mark.django_db
class TestSettingRaci:
    def test_a_project_admin_sets_roles_and_several_departments_may_be_responsible(
        self, session_client, project, issue, departments
    ):
        body = _body(
            (departments["rm"], "responsible"), (departments["qa"], "responsible"), (departments["pr"], "approver")
        )

        response = session_client.put(_url(project, issue), body, format="json")

        assert response.status_code == 200, response.data
        assert _roles(issue) == {
            str(departments["rm"].id): "responsible",
            str(departments["qa"].id): "responsible",
            str(departments["pr"].id): "approver",
        }
        read = session_client.get(_url(project, issue))
        assert read.status_code == 200 and read.data["can_edit"] is True
        assert sorted((row["group_id"], row["role"]) for row in read.data["raci"]) == sorted(
            (str(g.id), r)
            for g, r in (
                (departments["rm"], "responsible"),
                (departments["qa"], "responsible"),
                (departments["pr"], "approver"),
            )
        )

    def test_a_new_list_replaces_the_old_one(self, session_client, project, issue, departments):
        url = _url(project, issue)
        session_client.put(
            url, _body((departments["rm"], "responsible"), (departments["qa"], "consulted")), format="json"
        )

        session_client.put(url, _body((departments["qa"], "informed")), format="json")
        assert _roles(issue) == {str(departments["qa"].id): "informed"}

        session_client.put(url, {"raci": []}, format="json")
        assert _roles(issue) == {}

    def test_one_role_per_department(self, session_client, project, issue, departments):
        body = _body((departments["rm"], "responsible"), (departments["rm"], "approver"))

        response = session_client.put(_url(project, issue), body, format="json")

        assert response.status_code == 400
        assert not IssueRaci.objects.filter(issue=issue).exists()

    @pytest.mark.parametrize("role", ["owner", "R", "", None])
    def test_an_unknown_role_is_refused(self, session_client, project, issue, departments, role):
        body = {"raci": [{"group_id": str(departments["rm"].id), "role": role}]}

        assert session_client.put(_url(project, issue), body, format="json").status_code == 400

    def test_only_departments_of_the_workspace_get_roles(self, session_client, project, issue, workspace, create_user):
        plain = UserGroup.objects.create(workspace=workspace, name="Sales")
        from plane.db.models import Workspace

        other = Workspace.objects.create(name="Other", slug="other-raci", owner=create_user)
        foreign = _department(other, "Foreign", "FO")

        for group in (plain, foreign):
            response = session_client.put(_url(project, issue), _body((group, "consulted")), format="json")
            assert response.status_code == 400
        assert not IssueRaci.objects.filter(issue=issue).exists()

    def test_a_switched_off_department_keeps_its_role_but_gets_no_new_one(
        self, session_client, project, issue, departments
    ):
        url = _url(project, issue)
        session_client.put(url, _body((departments["rm"], "responsible")), format="json")
        UserGroup.objects.filter(pk=departments["rm"].pk).update(is_active=False)
        UserGroup.objects.filter(pk=departments["qa"].pk).update(is_active=False)

        keep = session_client.put(
            url, _body((departments["rm"], "responsible"), (departments["pr"], "informed")), format="json"
        )
        change = session_client.put(url, _body((departments["rm"], "approver")), format="json")
        new = session_client.put(url, _body((departments["qa"], "informed")), format="json")

        assert keep.status_code == 200
        assert change.status_code == 400 and new.status_code == 400
        assert _roles(issue) == {str(departments["rm"].id): "responsible", str(departments["pr"].id): "informed"}

    def test_the_project_lead_may_edit(self, workspace, project, issue, departments):
        lead = _person(workspace, project, "lead@example.com")
        Project.objects.filter(pk=project.pk).update(project_lead=lead)

        response = _client(lead).put(_url(project, issue), _body((departments["rm"], "approver")), format="json")

        assert response.status_code == 200

    def test_a_member_reads_but_may_not_edit(self, workspace, project, issue, departments):
        member = _person(workspace, project, "member@example.com")

        read = _client(member).get(_url(project, issue))
        write = _client(member).put(_url(project, issue), _body((departments["rm"], "approver")), format="json")

        assert read.status_code == 200 and read.data["can_edit"] is False
        assert write.status_code == 403
        assert not IssueRaci.objects.filter(issue=issue).exists()

    def test_a_restricted_guest_only_reads_the_work_items_they_created(self, workspace, project, issue, departments):
        guest = _person(workspace, project, "guest@example.com", role=GUEST)
        own = _issue(project, "Own", created_by=guest)

        assert _client(guest).get(_url(project, issue)).status_code == 403
        assert _client(guest).get(_url(project, own)).status_code == 200
        assert (
            _client(guest).put(_url(project, own), _body((departments["rm"], "approver")), format="json").status_code
            == 403
        )

    def test_a_stranger_gets_nothing(self, project, issue):
        stranger = User.objects.create(email="stranger@example.com", username="stranger")

        assert _client(stranger).get(_url(project, issue)).status_code == 403

    def test_refused_while_the_project_switch_is_off(self, session_client, project, issue, departments):
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)

        assert session_client.get(_url(project, issue)).status_code == 400
        assert (
            session_client.put(_url(project, issue), _body((departments["rm"], "approver")), format="json").status_code
            == 400
        )

    def test_refused_while_the_workspace_switch_is_off(self, session_client, workspace, project, issue, departments):
        WorkspaceFeature.objects.filter(workspace=workspace, key="raci").update(is_enabled=False)

        assert session_client.get(_url(project, issue)).status_code == 400

    def test_a_change_is_recorded_in_the_activity(
        self, session_client, project, issue, departments, _no_background_work
    ):
        url = _url(project, issue)
        session_client.put(url, _body((departments["rm"], "responsible")), format="json")
        _no_background_work.delay.reset_mock()

        session_client.put(url, _body((departments["rm"], "responsible")), format="json")
        assert not _no_background_work.delay.called  # nothing changed, nothing recorded

        session_client.put(url, _body((departments["rm"], "approver")), format="json")
        kwargs = _no_background_work.delay.call_args.kwargs
        assert kwargs["type"] == "raci.activity.updated"
        assert json.loads(kwargs["current_instance"])["raci"] == [
            {"group_id": str(departments["rm"].id), "role": "responsible"}
        ]
        assert json.loads(kwargs["requested_data"])["raci"] == [
            {"group_id": str(departments["rm"].id), "role": "approver"}
        ]


@pytest.mark.contract
@pytest.mark.django_db
class TestRaciActivity:
    def test_one_entry_per_department_with_its_roles(self, project, issue, departments, create_user):
        before = [
            {"group_id": str(departments["rm"].id), "role": "responsible"},
            {"group_id": str(departments["qa"].id), "role": "consulted"},
        ]
        after = [
            {"group_id": str(departments["rm"].id), "role": "approver"},
            {"group_id": str(departments["pr"].id), "role": "informed"},
        ]
        entries = []

        update_raci_activity(
            requested_data=json.dumps({"raci": after}),
            current_instance=json.dumps({"raci": before}),
            issue_id=issue.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            actor_id=create_user.id,
            issue_activities=entries,
            epoch=1,
        )

        found = {(entry.comment, entry.verb, entry.old_value, entry.new_value) for entry in entries}
        assert found == {
            ("RM · Marketing", "updated", "responsible", "approver"),
            ("QA · Quality", "deleted", "consulted", ""),
            ("PR · Production", "created", "", "informed"),
        }
        assert all(entry.field == "raci" for entry in entries)


@pytest.mark.contract
@pytest.mark.django_db
class TestRaciInWorkItemLists:
    def _list(self, client, project, params=None):
        response = client.get(f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/", params or {})
        assert response.status_code == 200, response.data
        return {row["name"]: row for row in response.data["results"]}

    def test_the_list_and_the_detail_carry_the_roles(self, session_client, project, issue, departments):
        IssueRaci.objects.create(
            issue=issue, group=departments["rm"], role="responsible", project=project, workspace=project.workspace
        )

        rows = self._list(session_client, project)
        detail = session_client.get(
            f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/{issue.id}/"
        )

        expected = [{"group_id": str(departments["rm"].id), "role": "responsible"}]
        assert [{k: str(v) for k, v in row.items()} for row in rows["Packaging"]["raci"]] == expected
        assert [{k: str(v) for k, v in row.items()} for row in detail.data["raci"]] == expected

    def test_nothing_is_served_while_the_project_has_raci_off(self, session_client, project, issue, departments):
        IssueRaci.objects.create(
            issue=issue, group=departments["rm"], role="responsible", project=project, workspace=project.workspace
        )
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)

        assert self._list(session_client, project)["Packaging"]["raci"] == []
        # the rows are kept for when it is switched on again
        assert IssueRaci.objects.filter(issue=issue).exists()

    def test_deleting_a_department_or_making_it_a_plain_group_removes_its_roles(
        self, session_client, workspace, project, issue, departments
    ):
        for key in ("rm", "qa"):
            IssueRaci.objects.create(
                issue=issue, group=departments[key], role="consulted", project=project, workspace=workspace
            )
        groups = f"/api/workspaces/{workspace.slug}/user-groups/"

        assert session_client.delete(f"{groups}{departments['rm'].id}/").status_code == 204
        assert (
            session_client.patch(f"{groups}{departments['qa'].id}/", {"kind": "group"}, format="json").status_code
            == 200
        )

        assert not IssueRaci.objects.filter(issue=issue).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestRaciFilters:
    @pytest.fixture
    def items(self, project, departments):
        parent = _issue(project, "Parent")
        made = {
            "Parent": parent,
            "Child": _issue(project, "Child", parent=parent),
            "Other": _issue(project, "Other"),
            "None": _issue(project, "None"),
        }
        for name, department, role in (
            ("Parent", "rm", "responsible"),
            ("Child", "rm", "consulted"),
            ("Other", "qa", "approver"),
        ):
            IssueRaci.objects.create(
                issue=made[name], group=departments[department], role=role, project=project, workspace=project.workspace
            )
        return made

    def _names(self, client, project, filters, sub_issue=True):
        params = {"filters": json.dumps(filters)}
        if not sub_issue:
            params["sub_issue"] = "false"
        response = client.get(f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/issues/", params)
        assert response.status_code == 200, response.data
        return sorted(row["name"] for row in response.data["results"])

    def test_a_department_with_any_role_includes_sub_work_items(self, session_client, project, departments, items):
        found = self._names(session_client, project, {"raci_department_id__in": str(departments["rm"].id)})

        assert found == ["Child", "Parent"]

    def test_a_department_with_one_role(self, session_client, project, departments, items):
        responsible = self._names(session_client, project, {"raci_responsible_id__in": str(departments["rm"].id)})
        approver = self._names(session_client, project, {"raci_approver_id": str(departments["qa"].id)})

        assert responsible == ["Parent"]
        assert approver == ["Other"]

    def test_my_department_is_the_department_group_the_person_is_in(self, workspace, project, departments, items):
        person = _person(workspace, project, "qa@example.com")
        UserGroupMember.objects.create(workspace=workspace, group=departments["qa"], user=person)

        assert self._names(_client(person), project, {"raci_department_id__in": "my_department"}) == ["Other"]

    def test_my_department_finds_nothing_for_a_person_without_one(self, session_client, project, items):
        assert self._names(session_client, project, {"raci_department_id__in": "my_department"}) == []

    def test_a_switched_off_department_is_nobodys_department(self, workspace, project, departments, items):
        person = _person(workspace, project, "qa2@example.com")
        UserGroupMember.objects.create(workspace=workspace, group=departments["qa"], user=person)
        UserGroup.objects.filter(pk=departments["qa"].pk).update(is_active=False)

        assert self._names(_client(person), project, {"raci_department_id__in": "my_department"}) == []

    def test_filters_find_nothing_while_the_project_has_raci_off(self, session_client, project, departments, items):
        Project.objects.filter(pk=project.pk).update(is_raci_enabled=False)

        assert self._names(session_client, project, {"raci_department_id__in": str(departments["rm"].id)}) == []


@pytest.mark.contract
@pytest.mark.django_db
class TestRaciInProjectCopies:
    def test_the_copy_of_the_work_items_carries_the_roles(self, session_client, workspace, project, issue, departments):
        from plane.bgtasks.project_copy_task import copy_project_work_items
        from plane.db.models import ProjectCopyJob

        IssueRaci.objects.create(
            issue=issue, group=departments["rm"], role="responsible", project=project, workspace=workspace
        )
        cache.clear()
        with mock.patch.object(copy_project_work_items, "delay"):
            response = session_client.post(
                f"/api/workspaces/{workspace.slug}/projects/{project.id}/duplicate/",
                {"include": {"work_items": True}},
                format="json",
            )
        assert response.status_code == 201, response.data
        job = ProjectCopyJob.objects.get(target_project_id=response.data["id"])
        copy_project_work_items(str(job.id))

        copy = Project.objects.get(pk=response.data["id"])
        copied = Issue.objects.get(project=copy, name="Packaging")
        assert copy.is_raci_enabled is True
        assert list(IssueRaci.objects.filter(issue=copied).values_list("group_id", "role")) == [
            (departments["rm"].id, "responsible")
        ]

    def test_the_roles_can_be_left_out(self, session_client, workspace, project, issue, departments):
        from plane.bgtasks.project_copy_task import copy_project_work_items
        from plane.db.models import ProjectCopyJob

        IssueRaci.objects.create(
            issue=issue, group=departments["rm"], role="responsible", project=project, workspace=workspace
        )
        cache.clear()
        with mock.patch.object(copy_project_work_items, "delay"):
            response = session_client.post(
                f"/api/workspaces/{workspace.slug}/projects/{project.id}/duplicate/",
                {"include": {"work_items": True}, "work_item_properties": ["assignees"]},
                format="json",
            )
        job = ProjectCopyJob.objects.get(target_project_id=response.data["id"])
        copy_project_work_items(str(job.id))
        job.refresh_from_db()

        assert not IssueRaci.objects.filter(project_id=response.data["id"]).exists()
        assert "work_items:raci-not-copied" in job.skipped
