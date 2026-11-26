# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI helpers: what changed between two lists of roles, the filter values, the checks of a list and storing it."""

import uuid

import pytest
from django.db import IntegrityError, transaction

from plane.db.models import (
    GroupKind,
    Issue,
    IssueRaci,
    Project,
    State,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceFeature,
    WorkspaceMember,
)
from plane.utils.raci import (
    MY_DEPARTMENT,
    RaciError,
    clean_raci,
    department_ids_of,
    project_raci_enabled,
    raci_changes,
    set_issue_raci,
    split_department_tokens,
)

A = str(uuid.uuid4())
B = str(uuid.uuid4())
C = str(uuid.uuid4())


@pytest.mark.unit
class TestPureHelpers:
    def test_changes_name_added_changed_and_removed_departments(self):
        before = [{"group_id": A, "role": "responsible"}, {"group_id": B, "role": "consulted"}]
        after = [{"group_id": A, "role": "approver"}, {"group_id": C, "role": "informed"}]

        assert sorted(raci_changes(before, after)) == sorted(
            [(A, "responsible", "approver"), (B, "consulted", None), (C, None, "informed")]
        )

    def test_no_change_no_entries(self):
        same = [{"group_id": A, "role": "responsible"}]
        assert raci_changes(same, list(same)) == []
        assert raci_changes(None, []) == []

    def test_filter_values_are_ids_and_my_department_and_rubbish_is_ignored(self):
        ids, mine = split_department_tokens(f"{A}, my_department,,null,nonsense")

        assert ids == {uuid.UUID(A)} and mine is True
        assert split_department_tokens(None) == (set(), False)
        assert split_department_tokens([MY_DEPARTMENT]) == (set(), True)


@pytest.mark.unit
@pytest.mark.django_db
class TestStoringRaci:
    @pytest.fixture
    def ws(self, create_user):
        workspace = Workspace.objects.create(name="W", slug="raci-unit", owner=create_user)
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    @pytest.fixture
    def issue(self, ws, create_user):
        project = Project.objects.create(name="P", identifier="PRJ", workspace=ws, created_by=create_user)
        state = State.objects.create(name="Todo", group="unstarted", color="#fff", project=project, workspace=ws)
        return Issue.objects.create(name="I", project=project, workspace=ws, state=state)

    def _department(self, ws, name, **extra):
        return UserGroup.objects.create(workspace=ws, name=name, kind=GroupKind.DEPARTMENT, **extra)

    def test_a_department_has_one_live_row_per_work_item(self, ws, issue):
        department = self._department(ws, "Quality")
        IssueRaci.objects.create(issue=issue, group=department, role="responsible", project=issue.project, workspace=ws)

        with pytest.raises(IntegrityError), transaction.atomic():
            IssueRaci.objects.create(
                issue=issue, group=department, role="approver", project=issue.project, workspace=ws
            )

    def test_storing_creates_changes_and_removes_rows(self, ws, issue, create_user):
        quality = self._department(ws, "Quality")
        sales = self._department(ws, "Sales")

        set_issue_raci(issue, {quality.id: "responsible", sales.id: "responsible"}, actor=create_user)
        before, after = set_issue_raci(issue, {quality.id: "approver"}, actor=create_user)

        assert {row["role"] for row in before} == {"responsible"} and len(before) == 2
        assert after == [{"group_id": str(quality.id), "role": "approver"}]

    def test_a_plain_group_is_not_a_department(self, ws, issue):
        plain = UserGroup.objects.create(workspace=ws, name="Sales")

        with pytest.raises(RaciError):
            clean_raci(ws.id, issue.id, [{"group_id": str(plain.id), "role": "informed"}])

    def test_a_list_must_be_a_list_of_entries(self, ws, issue):
        for bad in (None, {"group_id": A}, ["x"], [{"group_id": "not-a-uuid", "role": "informed"}]):
            with pytest.raises(RaciError):
                clean_raci(ws.id, issue.id, bad)

    def test_my_departments_are_the_active_department_groups_of_the_person(self, ws, create_user):
        quality = self._department(ws, "Quality")
        closed = self._department(ws, "Closed", is_active=False)
        plain = UserGroup.objects.create(workspace=ws, name="Sales")
        for group in (quality, closed, plain):
            UserGroupMember.objects.create(workspace=ws, group=group, user=create_user)

        assert department_ids_of(create_user, ws.id) == {quality.id}
        assert department_ids_of(None, ws.id) == set()

    def test_raci_needs_the_workspace_and_the_project_switch(self, ws, issue):
        project = issue.project
        assert project_raci_enabled(project) is False

        Project.objects.filter(pk=project.pk).update(is_raci_enabled=True)
        project.refresh_from_db()
        assert project_raci_enabled(project) is False

        WorkspaceFeature.objects.create(workspace=ws, key="raci", is_enabled=True)
        project = Project.objects.get(pk=project.pk)
        assert project_raci_enabled(project) is True
