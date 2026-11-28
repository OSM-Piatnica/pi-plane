# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The initiatives of each project in the project list (roadmap F3): who gets them, and at what cost."""

from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from plane.db.models import (
    Initiative,
    InitiativeKind,
    InitiativeProject,
    Project,
    ProjectMember,
    User,
    WorkspaceFeature,
    WorkspaceMember,
)
from plane.utils.initiatives import add_initiative_ids, initiative_ids_of_projects

ADMIN, MEMBER, GUEST = 20, 15, 5


def _person(workspace, role=MEMBER):
    unique = uuid4().hex[:8]
    user = User.objects.create(email=f"person-{unique}@plane.so", username=f"person_{unique}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _project(workspace, identifier, members=(), role=MEMBER, guests_see_all=False):
    project = Project.objects.create(
        name=f"{identifier} project",
        identifier=identifier,
        workspace=workspace,
        guest_view_all_features=guests_see_all,
    )
    for user in members:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=role)
    return project


def _initiative(workspace, name, kind=InitiativeKind.INITIATIVE, **extra):
    return Initiative.objects.create(workspace=workspace, name=name, kind=kind, **extra)


def _link(initiative, *projects):
    for project in projects:
        InitiativeProject.objects.create(initiative=initiative, project=project)


@pytest.fixture
def initiatives_on(db, workspace):
    return WorkspaceFeature.objects.create(workspace=workspace, key="initiatives", is_enabled=True)


@pytest.mark.unit
@pytest.mark.django_db
class TestInitiativeIdsOfProjects:
    def test_a_project_in_two_initiatives_has_both_in_list_order(self, workspace, create_user, initiatives_on):
        project = _project(workspace, "TWO")
        first = _initiative(workspace, "First", sort_order=1)
        second = _initiative(workspace, "Second", sort_order=2)
        _link(second, project)
        _link(first, project)

        linked = initiative_ids_of_projects(create_user, workspace.id, [project.id])

        assert linked[project.id] == [first.id, second.id]

    def test_a_project_without_initiatives_is_not_in_the_result(self, workspace, create_user, initiatives_on):
        project = _project(workspace, "NONE")

        assert initiative_ids_of_projects(create_user, workspace.id, [project.id]) == {}

    def test_a_goal_is_not_listed_its_initiatives_are(self, workspace, create_user, initiatives_on):
        project = _project(workspace, "GOAL")
        goal = _initiative(workspace, "Goal", InitiativeKind.GOAL)
        initiative = _initiative(workspace, "Child", parent=goal)
        _link(initiative, project)

        assert initiative_ids_of_projects(create_user, workspace.id, [project.id])[project.id] == [initiative.id]

    def test_nothing_while_the_feature_is_off(self, workspace, create_user):
        project = _project(workspace, "OFF")
        _link(_initiative(workspace, "Hidden"), project)

        assert initiative_ids_of_projects(create_user, workspace.id, [project.id]) == {}

    def test_nothing_for_a_workspace_guest(self, workspace, initiatives_on):
        guest = _person(workspace, GUEST)
        project = _project(workspace, "WGU", [guest], role=GUEST, guests_see_all=True)
        _link(_initiative(workspace, "Hidden"), project)

        assert initiative_ids_of_projects(guest, workspace.id, [project.id]) == {}

    def test_only_projects_whose_numbers_the_person_may_see(self, workspace, initiatives_on):
        member = _person(workspace)
        mine = _project(workspace, "MINE", [member])
        guest_all = _project(workspace, "GALL", [member], role=GUEST, guests_see_all=True)
        guest_own = _project(workspace, "GOWN", [member], role=GUEST)
        public = _project(workspace, "PUB")
        initiative = _initiative(workspace, "Shared")
        _link(initiative, mine, guest_all, guest_own, public)

        linked = initiative_ids_of_projects(member, workspace.id, [mine.id, guest_all.id, guest_own.id, public.id])

        assert set(linked) == {mine.id, guest_all.id}

    def test_a_workspace_admin_gets_every_project(self, workspace, create_user, initiatives_on):
        outside = _project(workspace, "OUT")
        initiative = _initiative(workspace, "Admin")
        _link(initiative, outside)

        assert initiative_ids_of_projects(create_user, workspace.id, [outside.id]) == {outside.id: [initiative.id]}

    def test_a_deleted_initiative_is_left_out(self, workspace, create_user, initiatives_on):
        project = _project(workspace, "DEL")
        initiative = _initiative(workspace, "Gone")
        _link(initiative, project)
        initiative.delete()

        assert initiative_ids_of_projects(create_user, workspace.id, [project.id]) == {}

    def test_the_number_of_queries_does_not_grow_with_the_number_of_projects(self, workspace, initiatives_on):
        member = _person(workspace)

        def build(number, prefix):
            projects = [_project(workspace, f"{prefix}{index}", [member]) for index in range(number)]
            for index, project in enumerate(projects):
                _link(_initiative(workspace, f"{prefix} {index}"), project)
            return [project.id for project in projects]

        few, many = build(1, "F"), build(8, "M")

        with CaptureQueriesContext(connection) as small:
            initiative_ids_of_projects(member, workspace.id, few)
        with CaptureQueriesContext(connection) as large:
            initiative_ids_of_projects(member, workspace.id, many)

        assert len(large) == len(small)


@pytest.mark.unit
@pytest.mark.django_db
class TestAddInitiativeIds:
    def test_every_row_gets_a_list_of_text_ids(self, workspace, create_user, initiatives_on):
        linked = _project(workspace, "LNK")
        lonely = _project(workspace, "LON")
        initiative = _initiative(workspace, "One")
        _link(initiative, linked)

        rows = add_initiative_ids(create_user, workspace.id, [{"id": str(linked.id)}, {"id": lonely.id}])

        assert rows == [
            {"id": str(linked.id), "initiative_ids": [str(initiative.id)]},
            {"id": lonely.id, "initiative_ids": []},
        ]
