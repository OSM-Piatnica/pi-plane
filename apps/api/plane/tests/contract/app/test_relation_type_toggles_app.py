# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project toggles for the relation types: blocking is always on, the other groups follow the project's flags."""

import importlib
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember
from plane.utils.issue_relation_types import ALL_RELATION_NAMES
from plane.utils.relation_type_toggles import RELATION_TOGGLE_BY_TYPE, RELATION_TYPE_DISABLED

GROUPS = {
    "is_relation_schedule_enabled": [
        "start_before",
        "start_after",
        "finish_before",
        "finish_after",
        "start_before_finish",
        "finish_after_start",
    ],
    "is_relation_traceability_enabled": [
        "implemented_by",
        "implements",
        "caused_by",
        "causes",
        "cloned_by",
        "clones",
        "tested_by",
        "tests",
    ],
    "is_relation_relates_to_enabled": ["relates_to"],
    "is_relation_duplicate_enabled": ["duplicate"],
}


@pytest.fixture(autouse=True)
def _no_activity(db):
    with (
        mock.patch("plane.app.views.issue.relation.issue_activity"),
        mock.patch("plane.app.views.issue.relation.base_host", return_value="http://testserver"),
        mock.patch("plane.api.views.issue.issue_activity"),
        mock.patch("plane.api.views.issue.base_host", return_value="http://testserver"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Tog", identifier="TOG", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def items(project):
    return [Issue.objects.create(name=name, project=project, workspace=project.workspace) for name in "ab"]


def url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/issue-relation/"


def relate(client, workspace, project, issue, relation_type, other):
    return client.post(
        url(workspace, project, issue),
        {"relation_type": relation_type, "issues": [str(other.id)]},
        format="json",
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestDefaults:
    def test_only_relates_to_and_duplicate_are_on_by_default(self, project):
        assert project.is_relation_relates_to_enabled is True
        assert project.is_relation_duplicate_enabled is True
        assert project.is_relation_schedule_enabled is False
        assert project.is_relation_traceability_enabled is False

    def test_every_type_but_blocking_belongs_to_a_group(self):
        assert set(RELATION_TOGGLE_BY_TYPE) == set(ALL_RELATION_NAMES) - {"blocked_by", "blocking"}
        assert {name for names in GROUPS.values() for name in names} == set(RELATION_TOGGLE_BY_TYPE)

    def test_creating_a_project_accepts_the_flags(self, session_client, workspace):
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/",
            {
                "name": "Flags",
                "identifier": "FLG",
                "is_relation_schedule_enabled": True,
                "is_relation_duplicate_enabled": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        project = Project.objects.get(pk=response.data["id"])
        assert project.is_relation_schedule_enabled is True
        assert project.is_relation_duplicate_enabled is False
        assert project.is_relation_relates_to_enabled is True


@pytest.mark.contract
@pytest.mark.django_db
class TestEnforcement:
    def test_blocking_is_always_available(self, session_client, workspace, project, items):
        a, b = items
        Project.objects.filter(pk=project.pk).update(**{flag: False for flag in GROUPS})
        assert relate(session_client, workspace, project, a, "blocked_by", b).status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize(
        "flag,relation_type",
        [(flag, name) for flag, names in GROUPS.items() for name in names],
    )
    def test_a_type_is_refused_when_its_group_is_off(
        self, session_client, workspace, project, items, flag, relation_type
    ):
        a, b = items
        Project.objects.filter(pk=project.pk).update(**{flag: False})

        response = relate(session_client, workspace, project, a, relation_type, b)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == RELATION_TYPE_DISABLED
        assert not IssueRelation.objects.filter(issue__in=items).exists()

    @pytest.mark.parametrize(
        "flag,relation_type",
        [(flag, names[0]) for flag, names in GROUPS.items()],
    )
    def test_a_type_is_allowed_when_its_group_is_on(
        self, session_client, workspace, project, items, flag, relation_type
    ):
        a, b = items
        Project.objects.filter(pk=project.pk).update(**{flag: True})

        assert relate(session_client, workspace, project, a, relation_type, b).status_code == status.HTTP_201_CREATED

    def test_one_group_off_leaves_the_others(self, session_client, workspace, project, items):
        a, b = items
        Project.objects.filter(pk=project.pk).update(
            is_relation_traceability_enabled=True, is_relation_schedule_enabled=False
        )

        assert relate(session_client, workspace, project, a, "caused_by", b).status_code == status.HTTP_201_CREATED
        assert (
            relate(session_client, workspace, project, a, "start_before", b).status_code == status.HTTP_400_BAD_REQUEST
        )

    def test_existing_relations_stay_listed_and_removable_after_switching_off(
        self, session_client, workspace, project, items
    ):
        a, b = items
        Project.objects.filter(pk=project.pk).update(is_relation_traceability_enabled=True)
        relate(session_client, workspace, project, a, "caused_by", b)
        Project.objects.filter(pk=project.pk).update(is_relation_traceability_enabled=False)

        listed = session_client.get(url(workspace, project, a)).json()
        assert [row["id"] for row in listed["caused_by"]] == [str(b.id)]

        removed = session_client.post(
            url(workspace, project, a) + "remove/",
            {"related_issue": str(b.id), "relation_type": "caused_by"},
            format="json",
        )
        assert removed.status_code == status.HTTP_204_NO_CONTENT, removed.content

    def test_the_public_api_refuses_a_type_that_is_off(self, api_key_client, workspace, project, items):
        a, b = items
        api_url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{a.id}/relations/"

        refused = api_key_client.post(api_url, {"relation_type": "tested_by", "issues": [str(b.id)]}, format="json")
        assert refused.status_code == status.HTTP_400_BAD_REQUEST
        assert refused.json()["error_code"] == RELATION_TYPE_DISABLED

        Project.objects.filter(pk=project.pk).update(is_relation_traceability_enabled=True)
        allowed = api_key_client.post(api_url, {"relation_type": "tested_by", "issues": [str(b.id)]}, format="json")
        assert allowed.status_code == status.HTTP_201_CREATED, allowed.data


@pytest.mark.contract
@pytest.mark.django_db
class TestMigration:
    def test_groups_in_use_are_switched_on_for_existing_projects(self, workspace, create_user):
        migration = importlib.import_module("plane.db.migrations.0146_project_relation_type_toggles")
        used = Project.objects.create(name="Used", identifier="USD", workspace=workspace, created_by=create_user)
        idle = Project.objects.create(name="Idle", identifier="IDL", workspace=workspace, created_by=create_user)
        issues = [Issue.objects.create(name=str(n), project=used, workspace=workspace) for n in range(2)]
        IssueRelation.objects.create(
            issue=issues[0], related_issue=issues[1], relation_type="start_before", project=used, workspace=workspace
        )

        from django.apps import apps

        migration.enable_groups_in_use(apps, None)

        used.refresh_from_db()
        idle.refresh_from_db()
        assert used.is_relation_schedule_enabled is True
        assert used.is_relation_traceability_enabled is False
        assert idle.is_relation_schedule_enabled is False
