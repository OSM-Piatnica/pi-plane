# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Initiatives: what the models refuse, and the progress rolled up from projects for one person."""

from datetime import date
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from plane.db.models import (
    Initiative,
    InitiativeEpic,
    InitiativeKind,
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
from plane.bgtasks.deletion_task import soft_delete_related_objects
from plane.utils.initiatives import describe, empty_progress, linked_epics, project_access, roll_up, roll_up_epics

GOAL, INITIATIVE = InitiativeKind.GOAL, InitiativeKind.INITIATIVE


@pytest.mark.unit
class TestRollUp:
    def test_the_state_groups_of_the_visible_projects_are_added_up(self):
        counts = {"a": {"backlog": 2, "completed": 1}, "b": {"completed": 3, "started": 1}}

        result = roll_up(["a", "b"], {"a", "b"}, counts)

        assert result["progress"] == {
            "total_issues": 7,
            "backlog": 2,
            "unstarted": 0,
            "started": 1,
            "completed": 4,
            "cancelled": 0,
        }
        assert result["progress_is_partial"] is False
        assert result["hidden_project_count"] == 0

    def test_a_project_given_twice_is_counted_once(self):
        result = roll_up(["a", "a", "b"], {"a", "b"}, {"a": {"started": 5}, "b": {"started": 1}})

        assert result["progress"]["started"] == 6
        assert result["progress"]["total_issues"] == 6

    def test_a_project_the_person_is_not_in_is_left_out_and_only_counted_as_hidden(self):
        result = roll_up(["a", "b", "c"], {"a"}, {"a": {"started": 1}, "b": {"started": 10}, "c": {"backlog": 4}})

        assert result["progress"]["total_issues"] == 1
        assert result["progress_is_partial"] is True
        assert result["hidden_project_count"] == 2

    def test_nothing_linked_is_an_empty_complete_progress(self):
        assert roll_up([], set(), {}) == {
            "progress": empty_progress(),
            "progress_is_partial": False,
            "hidden_project_count": 0,
        }


@pytest.mark.unit
class TestRollUpEpics:
    def test_the_children_of_each_epic_are_added_up_once(self):
        counts = {"a": {"started": 2}, "b": {"completed": 1, "backlog": 1}}

        result = roll_up_epics(["a", "b", "a"], 0, counts, set())

        assert result["epic_progress"] == {
            **empty_progress(),
            "total_issues": 4,
            "started": 2,
            "completed": 1,
            "backlog": 1,
        }
        assert result["epic_progress_is_partial"] is False

    def test_hidden_epics_make_it_partial_without_adding_anything(self):
        result = roll_up_epics(["a"], 2, {"a": {"started": 1}, "b": {"started": 9}}, set())

        assert result["epic_progress"]["total_issues"] == 1
        assert result["epic_progress_is_partial"] is True

    def test_an_epic_with_children_the_person_may_not_see_makes_it_partial(self):
        assert roll_up_epics(["a"], 0, {}, {"a"})["epic_progress_is_partial"] is True
        assert roll_up_epics(["a"], 0, {}, {"b"})["epic_progress_is_partial"] is False

    def test_no_epics_is_an_empty_complete_figure(self):
        assert roll_up_epics([], 0, {}, set()) == {"epic_progress": empty_progress(), "epic_progress_is_partial": False}


def _initiative(workspace, name="Thing", kind=INITIATIVE, **extra):
    return Initiative.objects.create(workspace=workspace, name=name, kind=kind, **extra)


def _project(workspace, identifier, members=()):
    project = Project.objects.create(name=f"{identifier} project", identifier=identifier, workspace=workspace)
    for user in members:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=15)
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


@pytest.mark.unit
@pytest.mark.django_db
class TestInitiativeModels:
    def test_a_goal_cannot_have_a_parent(self, workspace):
        goal = _initiative(workspace, "Goal", GOAL)

        with pytest.raises(ValidationError):
            _initiative(workspace, "Another goal", GOAL, parent=goal)

    def test_the_parent_of_an_initiative_must_be_a_goal(self, workspace):
        goal = _initiative(workspace, "Goal", GOAL)
        first = _initiative(workspace, "First", parent=goal)

        assert first.parent_id == goal.id
        with pytest.raises(ValidationError):
            _initiative(workspace, "Second", parent=first)

    def test_the_parent_must_be_in_the_same_workspace(self, workspace, create_user):
        other = Workspace.objects.create(name="Other", slug="other-workspace", owner=create_user)
        goal = _initiative(other, "Their goal", GOAL)

        with pytest.raises(ValidationError):
            _initiative(workspace, "Ours", parent=goal)

    def test_the_target_date_cannot_be_before_the_start_date(self, workspace):
        with pytest.raises(ValidationError):
            _initiative(workspace, start_date=date(2026, 5, 2), target_date=date(2026, 5, 1))

        same_day = _initiative(workspace, start_date=date(2026, 5, 1), target_date=date(2026, 5, 1))
        assert same_day.pk is not None

    def test_unknown_kind_status_and_health_are_refused(self, workspace):
        for field, value in (("kind", "programme"), ("status", "done"), ("health", "fine")):
            with pytest.raises(ValidationError):
                _initiative(workspace, **{field: value})

    def test_a_new_one_goes_to_the_end_of_the_list(self, workspace):
        first = _initiative(workspace, "First")
        second = _initiative(workspace, "Second")

        assert second.sort_order > first.sort_order

    def test_a_project_is_linked_to_an_initiative_of_its_own_workspace_only(self, workspace, create_user):
        other = Workspace.objects.create(name="Other", slug="other-workspace", owner=create_user)
        initiative = _initiative(workspace)
        goal = _initiative(workspace, "Goal", GOAL)

        link = InitiativeProject.objects.create(initiative=initiative, project=_project(workspace, "OWN"))

        assert link.workspace_id == workspace.id
        with pytest.raises(ValidationError):
            InitiativeProject.objects.create(initiative=initiative, project=_project(other, "OTH"))
        with pytest.raises(ValidationError):
            InitiativeProject.objects.create(initiative=goal, project=_project(workspace, "GOA"))

    def test_only_an_epic_is_linked_as_an_epic(self, workspace):
        initiative = _initiative(workspace)
        project = _project(workspace, "EPI")
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        task_type = IssueType.objects.create(workspace=workspace, name="Task")
        epic = _issues(project, "started", 1, epic_type)[0]
        task = _issues(project, "started", 1, task_type)[0]
        untyped = _issues(project, "started", 1)[0]

        assert InitiativeEpic.objects.create(initiative=initiative, issue=epic).pk is not None
        for issue in (task, untyped):
            with pytest.raises(ValidationError):
                InitiativeEpic.objects.create(initiative=initiative, issue=issue)

    def test_an_update_needs_a_known_health(self, workspace, create_user):
        initiative = _initiative(workspace)

        update = InitiativeUpdate.objects.create(initiative=initiative, author=create_user, health="at_risk")

        assert update.workspace_id == workspace.id
        with pytest.raises(ValidationError):
            InitiativeUpdate.objects.create(initiative=initiative, author=create_user, health="fine")

    def test_a_link_can_be_removed_after_the_epic_was_given_another_type(self, workspace):
        initiative = _initiative(workspace)
        project = _project(workspace, "EPI")
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        task_type = IssueType.objects.create(workspace=workspace, name="Task")
        retyped = _issues(project, "started", 1, epic_type)[0]
        untyped = _issues(project, "started", 1, epic_type)[0]
        links = [InitiativeEpic.objects.create(initiative=initiative, issue=issue) for issue in (retyped, untyped)]
        Issue.objects.filter(pk=retyped.pk).update(type=task_type)
        Issue.objects.filter(pk=untyped.pk).update(type=None)

        for link in links:
            InitiativeEpic.objects.get(pk=link.pk).delete()

        assert not InitiativeEpic.objects.filter(initiative=initiative).exists()

    def test_deleting_an_initiative_removes_the_link_of_a_retyped_epic(self, workspace):
        initiative = _initiative(workspace)
        project = _project(workspace, "EPI")
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        epic = _issues(project, "started", 1, epic_type)[0]
        InitiativeEpic.objects.create(initiative=initiative, issue=epic)
        InitiativeProject.objects.create(initiative=initiative, project=project)
        Issue.objects.filter(pk=epic.pk).update(type=None)

        soft_delete_related_objects("db", "initiative", str(initiative.pk))

        assert not Initiative.objects.filter(pk=initiative.pk).exists()
        assert not InitiativeEpic.objects.filter(initiative_id=initiative.pk).exists()
        assert not InitiativeProject.objects.filter(initiative_id=initiative.pk).exists()

    def test_an_initiative_that_broke_a_rule_since_can_still_be_deleted(self, workspace):
        goal = _initiative(workspace, "Goal", GOAL)
        initiative = _initiative(workspace, parent=goal)
        Initiative.objects.filter(pk=goal.pk).update(kind=INITIATIVE)

        Initiative.objects.get(pk=initiative.pk).delete()

        assert not Initiative.objects.filter(pk=initiative.pk).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestDescribe:
    def _outsider(self, workspace):
        unique = uuid4().hex[:8]
        user = User.objects.create(email=f"outsider-{unique}@plane.so", username=f"outsider_{unique}")
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
        return user

    def test_an_initiative_counts_the_work_items_of_its_projects_without_epics(self, workspace, create_user):
        project = _project(workspace, "ONE", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        _issues(project, "backlog", 2)
        _issues(project, "completed", 3)
        epic = _issues(project, "started", 1, epic_type)[0]
        initiative = _initiative(workspace)
        InitiativeProject.objects.create(initiative=initiative, project=project)
        InitiativeEpic.objects.create(initiative=initiative, issue=epic)

        described = describe([initiative], create_user, workspace.id)[initiative.id]

        assert described["progress"] == {**empty_progress(), "total_issues": 5, "backlog": 2, "completed": 3}
        assert described["project_ids"] == [project.id]
        assert described["epic_ids"] == [epic.id]
        assert described["progress_is_partial"] is False

    def test_a_goal_counts_a_project_of_two_of_its_initiatives_once(self, workspace, create_user):
        shared = _project(workspace, "SHA", [create_user])
        single = _project(workspace, "SIN", [create_user])
        _issues(shared, "started", 4)
        _issues(single, "completed", 1)
        goal = _initiative(workspace, "Goal", GOAL)
        first = _initiative(workspace, "First", parent=goal)
        second = _initiative(workspace, "Second", parent=goal)
        InitiativeProject.objects.create(initiative=first, project=shared)
        InitiativeProject.objects.create(initiative=second, project=shared)
        InitiativeProject.objects.create(initiative=second, project=single)

        described = describe([goal, first, second], create_user, workspace.id)

        assert described[goal.id]["progress"] == {**empty_progress(), "total_issues": 5, "started": 4, "completed": 1}
        assert set(described[goal.id]["project_ids"]) == {shared.id, single.id}
        assert set(described[goal.id]["initiative_ids"]) == {first.id, second.id}
        assert described[first.id]["progress"]["total_issues"] == 4
        assert described[second.id]["progress"]["total_issues"] == 5

    def test_projects_the_person_is_not_in_are_hidden_and_make_the_progress_partial(self, workspace, create_user):
        outsider = self._outsider(workspace)
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        _issues(visible, "started", 1)
        _issues(secret, "started", 7)
        secret_epic = _issues(secret, "started", 1, epic_type)[0]
        goal = _initiative(workspace, "Goal", GOAL)
        initiative = _initiative(workspace, parent=goal)
        InitiativeProject.objects.create(initiative=initiative, project=visible)
        InitiativeProject.objects.create(initiative=initiative, project=secret)
        InitiativeEpic.objects.create(initiative=initiative, issue=secret_epic)

        for_member = describe([goal, initiative], create_user, workspace.id)
        for_outsider = describe([goal, initiative], outsider, workspace.id)

        assert for_member[initiative.id]["progress"]["total_issues"] == 8
        assert for_member[initiative.id]["progress_is_partial"] is False
        assert for_member[initiative.id]["epic_ids"] == [secret_epic.id]
        for item in (goal, initiative):
            assert for_outsider[item.id]["progress"]["total_issues"] == 1
            assert for_outsider[item.id]["progress_is_partial"] is True
            assert for_outsider[item.id]["hidden_project_count"] == 1
            assert for_outsider[item.id]["project_ids"] == [visible.id]
        assert for_outsider[initiative.id]["epic_ids"] == []
        assert for_outsider[initiative.id]["hidden_epic_count"] == 1

    def test_a_former_member_of_a_project_no_longer_gets_its_numbers(self, workspace, create_user):
        project = _project(workspace, "OLD")
        former = self._outsider(workspace)
        ProjectMember.objects.create(workspace=workspace, project=project, member=former, role=15, is_active=False)
        _issues(project, "started", 2)
        initiative = _initiative(workspace)
        InitiativeProject.objects.create(initiative=initiative, project=project)

        described = describe([initiative], former, workspace.id)[initiative.id]

        assert described["progress"]["total_issues"] == 0
        assert described["hidden_project_count"] == 1

    def test_the_number_of_queries_does_not_grow_with_the_number_of_initiatives(self, workspace, create_user):
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)

        def build(number, prefix):
            goal = _initiative(workspace, f"Goal {prefix}", GOAL)
            made = [goal]
            for index in range(number):
                project = _project(workspace, f"{prefix}{index}", [create_user])
                _issues(project, "started", 1)
                initiative = _initiative(workspace, f"{prefix} {index}", parent=goal)
                InitiativeProject.objects.create(initiative=initiative, project=project)
                InitiativeEpic.objects.create(initiative=initiative, issue=_issues(project, "backlog", 1, epic_type)[0])
                made.append(initiative)
            return made

        few, many = build(1, "F"), build(6, "M")

        with CaptureQueriesContext(connection) as small:
            describe(few, create_user, workspace.id)
        with CaptureQueriesContext(connection) as large:
            describe(many, create_user, workspace.id)

        assert len(large) == len(small)

    def _guest_of(self, workspace, project, workspace_role=15):
        user = self._outsider(workspace)
        WorkspaceMember.objects.filter(workspace=workspace, member=user).update(role=workspace_role)
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=5)
        return user

    def test_a_project_guest_who_sees_only_their_own_work_items_gets_no_numbers(self, workspace, create_user):
        project = _project(workspace, "GUE", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        _issues(project, "started", 3)
        epic = _issues(project, "started", 1, epic_type)[0]
        guest = self._guest_of(workspace, project)
        initiative = _initiative(workspace)
        InitiativeProject.objects.create(initiative=initiative, project=project)
        InitiativeEpic.objects.create(initiative=initiative, issue=epic)

        described = describe([initiative], guest, workspace.id)[initiative.id]

        assert project_access(guest, workspace.id) == (set(), set())
        assert described["progress"]["total_issues"] == 0
        assert described["progress_is_partial"] is True and described["hidden_project_count"] == 1
        assert described["project_ids"] == [] and described["epic_ids"] == []
        assert described["hidden_epic_count"] == 1

    def test_a_guest_of_a_project_that_shows_everything_to_guests_sees_but_does_not_manage(
        self, workspace, create_user
    ):
        project = _project(workspace, "OPE", [create_user])
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        _issues(project, "started", 3)
        guest = self._guest_of(workspace, project)
        initiative = _initiative(workspace)
        InitiativeProject.objects.create(initiative=initiative, project=project)

        described = describe([initiative], guest, workspace.id)[initiative.id]

        assert project_access(guest, workspace.id) == ({project.id}, set())
        assert described["progress"]["total_issues"] == 3
        assert described["progress_is_partial"] is False

    def test_a_workspace_admin_sees_and_links_every_project_of_the_workspace_whatever_their_role_in_it(
        self, workspace, create_user
    ):
        joined = _project(workspace, "JOI")
        other = _project(workspace, "OTH")
        admin = self._guest_of(workspace, joined, workspace_role=20)

        archived = _project(workspace, "ARC")
        Project.objects.filter(pk=archived.pk).update(archived_at=timezone.now())

        deleted = _project(workspace, "DEL")
        Project.objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())
        both, every = {joined.id, other.id}, {joined.id, other.id, archived.id}

        assert project_access(admin, workspace.id, [joined.id, other.id, deleted.id]) == (both, both)
        assert project_access(admin, workspace.id) == (every, every)

    def test_retyped_and_archived_epics_are_not_reported(self, workspace, create_user):
        project = _project(workspace, "ONE", [create_user])
        archived_project = _project(workspace, "ARC", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        kept, retyped, archived = _issues(project, "started", 3, epic_type)
        in_archived_project = _issues(archived_project, "started", 1, epic_type)[0]
        initiative = _initiative(workspace)
        for issue in (kept, retyped, archived, in_archived_project):
            InitiativeEpic.objects.create(initiative=initiative, issue=issue)
        Issue.objects.filter(pk=retyped.pk).update(type=None)
        Issue.objects.filter(pk=archived.pk).update(archived_at=timezone.now().date())
        Project.objects.filter(pk=archived_project.pk).update(archived_at=timezone.now())

        described = describe([initiative], create_user, workspace.id)[initiative.id]

        assert described["epic_ids"] == [kept.id]
        assert described["hidden_epic_count"] == 0

    def test_an_archived_project_stays_listed_and_its_work_items_do_not_count(self, workspace, create_user):
        live = _project(workspace, "LIV", [create_user])
        archived = _project(workspace, "ARC", [create_user])
        _issues(live, "started", 2)
        _issues(archived, "completed", 5)
        initiative = _initiative(workspace)
        InitiativeProject.objects.create(initiative=initiative, project=live)
        InitiativeProject.objects.create(initiative=initiative, project=archived)
        Project.objects.filter(pk=archived.pk).update(archived_at=timezone.now())

        described = describe([initiative], create_user, workspace.id)[initiative.id]

        assert set(described["project_ids"]) == {live.id, archived.id}
        assert described["progress"]["total_issues"] == 2
        assert described["progress_is_partial"] is False

    def test_a_goal_has_the_epics_of_its_initiatives_each_once(self, workspace, create_user):
        outsider = self._outsider(workspace)
        visible = _project(workspace, "VIS", [create_user, outsider])
        secret = _project(workspace, "SEC", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        shared, single = _issues(visible, "started", 2, epic_type)
        secret_epic = _issues(secret, "started", 1, epic_type)[0]
        goal = _initiative(workspace, "Goal", GOAL)
        first = _initiative(workspace, "First", parent=goal)
        second = _initiative(workspace, "Second", parent=goal)
        for initiative, issue in ((first, shared), (first, secret_epic), (second, shared), (second, single)):
            InitiativeEpic.objects.create(initiative=initiative, issue=issue)
        InitiativeEpic.objects.create(initiative=second, issue=secret_epic)

        for_member = describe([goal], create_user, workspace.id)[goal.id]
        for_outsider = describe([goal], outsider, workspace.id)[goal.id]

        assert sorted(for_member["epic_ids"], key=str) == sorted([shared.id, single.id, secret_epic.id], key=str)
        assert len(for_member["epic_ids"]) == 3
        assert for_member["hidden_epic_count"] == 0
        assert sorted(for_outsider["epic_ids"], key=str) == sorted([shared.id, single.id], key=str)
        assert for_outsider["hidden_epic_count"] == 1

    def test_a_workspace_admin_sees_the_numbers_and_epics_of_projects_they_are_not_in(self, workspace, create_user):
        member = self._outsider(workspace)
        project = _project(workspace, "NOT", [member])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        _issues(project, "started", 4)
        epic = _issues(project, "backlog", 1, epic_type)[0]
        plain = self._outsider(workspace)
        goal = _initiative(workspace, "Goal", GOAL)
        initiative = _initiative(workspace, parent=goal)
        InitiativeProject.objects.create(initiative=initiative, project=project)
        InitiativeEpic.objects.create(initiative=initiative, issue=epic)

        for_admin = describe([goal, initiative], create_user, workspace.id)
        for_plain = describe([goal, initiative], plain, workspace.id)

        assert not ProjectMember.objects.filter(project=project, member=create_user).exists()
        for item in (goal, initiative):
            assert for_admin[item.id]["progress"]["total_issues"] == 4
            assert for_admin[item.id]["progress_is_partial"] is False
            assert for_admin[item.id]["hidden_project_count"] == 0
            assert for_admin[item.id]["project_ids"] == [project.id]
            assert for_admin[item.id]["epic_ids"] == [epic.id]
            assert for_admin[item.id]["hidden_epic_count"] == 0
            assert for_plain[item.id]["progress"]["total_issues"] == 0
            assert for_plain[item.id]["progress_is_partial"] is True
            assert for_plain[item.id]["hidden_project_count"] == 1
            assert for_plain[item.id]["project_ids"] == [] and for_plain[item.id]["epic_ids"] == []
            assert for_plain[item.id]["hidden_epic_count"] == 1


def _children(epic, group, number, project=None):
    project = project or epic.project
    state, _ = State.objects.get_or_create(
        project=project, workspace=project.workspace, group=group, defaults={"name": group}
    )
    return [
        Issue.objects.create(
            name=f"child {index}", project=project, workspace=project.workspace, state=state, parent=epic
        )
        for index in range(number)
    ]


@pytest.mark.unit
@pytest.mark.django_db
class TestEpicProgress:
    def test_the_children_of_linked_epics_count_apart_from_the_projects(self, workspace, create_user):
        project = _project(workspace, "ONE", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        epic = _issues(project, "started", 1, epic_type)[0]
        nested = _children(epic, "started", 1)[0]
        Issue.objects.filter(pk=nested.pk).update(type=epic_type)  # an Epic under an Epic does not count
        _children(epic, "completed", 2)
        archived = _children(epic, "backlog", 1)[0]
        Issue.objects.filter(pk=archived.pk).update(archived_at=timezone.now().date())
        initiative = _initiative(workspace)
        InitiativeEpic.objects.create(initiative=initiative, issue=epic)

        described = describe([initiative], create_user, workspace.id)[initiative.id]

        assert described["progress"]["total_issues"] == 0
        assert described["epic_progress"] == {**empty_progress(), "total_issues": 2, "completed": 2}
        assert described["epic_progress_is_partial"] is False

    def test_linked_epics_are_described_in_the_order_they_were_linked(self, workspace, create_user):
        project = _project(workspace, "ONE", [create_user])
        epic_type = IssueType.objects.create(workspace=workspace, name="Epic", is_epic=True)
        first, second = _issues(project, "started", 2, epic_type)
        _children(second, "completed", 1)
        initiative = _initiative(workspace)
        InitiativeEpic.objects.create(initiative=initiative, issue=second)
        InitiativeEpic.objects.create(initiative=initiative, issue=first)

        rows = linked_epics(initiative, create_user, workspace.id)

        assert [row["id"] for row in rows] == [second.id, first.id]
        assert rows[0]["project_identifier"] == "ONE"
        assert rows[0]["progress"]["completed"] == 1
        assert rows[1]["progress"] == empty_progress()
