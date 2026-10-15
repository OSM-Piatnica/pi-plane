# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import Project, ProjectMember


@pytest.mark.contract
class TestProjectListExpand:
    """Contract tests for ``?expand=`` on GET /api/v1/workspaces/{slug}/projects/.

    Regression for https://github.com/makeplane/plane/issues/4639. ``updated_by``
    originally came back as a bare UUID because it was missing from the expansion
    mapper. Adding it was not enough: ``BaseModel.save`` leaves ``updated_by`` NULL
    until a record is first updated, and expanding a null relation emitted ``{}``
    rather than ``null``.
    """

    def get_url(self, workspace_slug):
        return f"/api/v1/workspaces/{workspace_slug}/projects/"

    def make_project(self, workspace, user, identifier, updated_by=None):
        """Create a project with the audit columns set explicitly.

        ``BaseModel.save()`` overwrites ``created_by``/``updated_by`` from the
        current request user (there is none here), so the values have to be
        written with a queryset update that bypasses ``save()``.
        """
        project = Project.objects.create(
            name=f"Project {identifier}",
            identifier=identifier,
            workspace=workspace,
            project_lead=user,
        )
        ProjectMember.objects.create(project=project, member=user, role=20)
        Project.objects.filter(pk=project.pk).update(created_by=user, updated_by=updated_by)
        project.refresh_from_db()
        return project

    def get_project(self, response, identifier):
        results = response.json()["results"]
        match = next((p for p in results if p["identifier"] == identifier), None)
        assert match is not None, f"{identifier} missing from results: {[p['identifier'] for p in results]}"
        return match

    @pytest.mark.django_db
    def test_expand_updated_by_returns_a_user_object(self, api_key_client, workspace, create_user):
        """The exact request from the issue: expand=created_by,updated_by,project_lead."""
        self.make_project(workspace, create_user, "EXP", updated_by=create_user)

        response = api_key_client.get(
            self.get_url(workspace.slug),
            {"expand": "created_by,updated_by,project_lead"},
        )

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        payload = self.get_project(response, "EXP")
        for field in ("created_by", "updated_by", "project_lead"):
            assert isinstance(payload[field], dict), f"{field} was not expanded: {payload[field]!r}"
            assert payload[field]["id"] == str(create_user.id)
            assert "display_name" in payload[field]

    @pytest.mark.django_db
    def test_expand_null_relation_returns_null(self, api_key_client, workspace, create_user):
        """A project that has never been edited has updated_by = NULL.

        Expanding it must stay ``null`` rather than becoming an empty object.
        """
        project = self.make_project(workspace, create_user, "NEW")
        assert project.updated_by_id is None, "fixture precondition: updated_by is null"

        response = api_key_client.get(
            self.get_url(workspace.slug),
            {"expand": "created_by,updated_by"},
        )

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        payload = self.get_project(response, "NEW")
        assert payload["updated_by"] is None
        assert isinstance(payload["created_by"], dict)

    @pytest.mark.django_db
    def test_without_expand_updated_by_stays_a_plain_id(self, api_key_client, workspace, create_user):
        self.make_project(workspace, create_user, "RAW", updated_by=create_user)

        response = api_key_client.get(self.get_url(workspace.slug))

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
        payload = self.get_project(response, "RAW")
        assert payload["updated_by"] == str(create_user.id)
