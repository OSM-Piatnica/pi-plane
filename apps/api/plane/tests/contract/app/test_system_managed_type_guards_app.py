# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the server-side guards on system-managed work item types (approval, review).

Only the feature that owns such a type links it to a project (`ensure_project_kind_type`). The API refuses to delete,
deactivate, link, unlink or re-scope one by hand with `400` and `error_code` `WORK_ITEM_TYPE_SYSTEM_MANAGED`; the
name, icon, description and properties stay editable.
"""

import pytest
from rest_framework import status

from plane.db.models import IssueType, IssueTypeKind, Project, ProjectIssueType, ProjectMember, ProjectTemplate
from plane.utils.project_issue_types import SYSTEM_MANAGED_TYPE_CODE, ensure_project_kind_type

TYPE_URL = "/api/workspaces/{slug}/issue-types/{pk}/"
TYPES_URL = "/api/workspaces/{slug}/issue-types/"
LINKS_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-types/"
LINK_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-types/{pk}/"
SEED_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-setup/from-project-template/"


def _linked(project, issue_type):
    return ProjectIssueType.objects.filter(project=project, issue_type=issue_type, deleted_at__isnull=True)


def _assert_refused(response):
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
    assert response.data["error_code"] == SYSTEM_MANAGED_TYPE_CODE
    assert isinstance(response.data["error"], str) and response.data["error"]


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Guards", identifier="GU", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def other_project(db, workspace, create_user):
    project = Project.objects.create(
        name="Other", identifier="OT", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def approval_type(db, project):
    return ensure_project_kind_type(project, IssueTypeKind.APPROVAL)


@pytest.fixture
def review_type(db, project):
    return ensure_project_kind_type(project, IssueTypeKind.REVIEW)


@pytest.fixture
def bug_type(db, workspace, project):
    issue_type = IssueType.objects.create(workspace=workspace, name="Bug")
    ProjectIssueType.objects.create(project=project, issue_type=issue_type, workspace=workspace)
    return issue_type


@pytest.mark.contract
@pytest.mark.django_db
class TestDeleteAndDeactivate:
    def test_deleting_a_system_managed_type_is_refused(self, session_client, workspace, approval_type, review_type):
        for issue_type in (approval_type, review_type):
            _assert_refused(session_client.delete(TYPE_URL.format(slug=workspace.slug, pk=issue_type.id)))
            assert IssueType.objects.filter(pk=issue_type.pk).exists()

    def test_deactivating_a_system_managed_type_is_refused(self, session_client, workspace, approval_type):
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id), {"is_active": False}, format="json"
        )
        _assert_refused(response)
        approval_type.refresh_from_db()
        assert approval_type.is_active

    def test_a_refused_deactivation_changes_nothing_else(self, session_client, workspace, approval_type):
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id),
            {"is_active": False, "name": "Sign-off"},
            format="json",
        )
        _assert_refused(response)
        approval_type.refresh_from_db()
        assert approval_type.name != "Sign-off"

    def test_name_icon_description_and_properties_stay_editable(
        self, session_client, workspace, project, approval_type
    ):
        logo = {"in_use": "icon", "icon": {"name": "check", "color": "#00aa00"}}
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id),
            {
                "name": "Sign-off",
                "logo_props": logo,
                "description": "Acceptance",
                "is_active": True,
                # what the type form sends back: the links it was given
                "project_ids": [str(project.id)],
                "properties": [{"title": "Batch", "property_type": "text"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        approval_type.refresh_from_db()
        assert approval_type.name == "Sign-off"
        assert approval_type.logo_props == logo
        assert approval_type.description == "Acceptance"
        assert approval_type.properties.filter(title="Batch", deleted_at__isnull=True).exists()
        assert _linked(project, approval_type).exists()

    def test_the_kind_cannot_be_changed_through_the_api(self, session_client, workspace, approval_type, bug_type):
        session_client.patch(TYPE_URL.format(slug=workspace.slug, pk=approval_type.id), {"kind": "standard"})
        session_client.patch(TYPE_URL.format(slug=workspace.slug, pk=bug_type.id), {"kind": "approval"})
        approval_type.refresh_from_db()
        bug_type.refresh_from_db()
        assert approval_type.kind == IssueTypeKind.APPROVAL
        assert bug_type.kind == IssueTypeKind.STANDARD

    def test_creating_with_a_system_managed_kind_makes_a_standard_type(self, session_client, workspace, project):
        response = session_client.post(
            TYPES_URL.format(slug=workspace.slug),
            {"name": "Fake approval", "kind": "approval", "project_ids": [str(project.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = IssueType.objects.get(pk=response.data["id"])
        assert created.kind == IssueTypeKind.STANDARD

    def test_a_standard_type_can_still_be_deactivated_and_deleted(self, session_client, workspace, bug_type):
        url = TYPE_URL.format(slug=workspace.slug, pk=bug_type.id)
        response = session_client.patch(url, {"is_active": False}, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data
        bug_type.refresh_from_db()
        assert not bug_type.is_active

        response = session_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not IssueType.objects.filter(pk=bug_type.pk).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectLinks:
    def test_the_type_form_cannot_unlink_a_system_managed_type(self, session_client, workspace, project, approval_type):
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id), {"project_ids": []}, format="json"
        )
        _assert_refused(response)
        assert _linked(project, approval_type).exists()

    def test_the_type_form_cannot_link_a_system_managed_type(
        self, session_client, workspace, project, other_project, approval_type
    ):
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id),
            {"project_ids": [str(project.id), str(other_project.id)]},
            format="json",
        )
        _assert_refused(response)
        assert not _linked(other_project, approval_type).exists()

    def test_the_type_form_keeps_links_to_archived_projects(
        self, session_client, workspace, project, other_project, approval_type
    ):
        from django.utils import timezone

        ensure_project_kind_type(other_project, IssueTypeKind.APPROVAL)
        other_project.archived_at = timezone.now()
        other_project.save()
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=approval_type.id),
            {"name": "Sign-off", "project_ids": [str(project.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert _linked(other_project, approval_type).exists()

    def test_the_type_form_still_changes_the_projects_of_a_standard_type(
        self, session_client, workspace, project, other_project, bug_type
    ):
        response = session_client.patch(
            TYPE_URL.format(slug=workspace.slug, pk=bug_type.id),
            {"project_ids": [str(other_project.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert _linked(other_project, bug_type).exists()
        assert not _linked(project, bug_type).exists()

    def test_unlinking_a_system_managed_type_is_refused(self, session_client, workspace, project, approval_type):
        link = _linked(project, approval_type).get()
        response = session_client.delete(LINK_URL.format(slug=workspace.slug, project_id=project.id, pk=link.id))
        _assert_refused(response)
        assert _linked(project, approval_type).exists()

    def test_linking_a_system_managed_type_by_hand_is_refused(
        self, session_client, workspace, other_project, approval_type
    ):
        response = session_client.post(
            LINKS_URL.format(slug=workspace.slug, project_id=other_project.id),
            {"issue_type_id": str(approval_type.id)},
            format="json",
        )
        _assert_refused(response)
        assert not _linked(other_project, approval_type).exists()

    def test_a_system_managed_type_cannot_become_the_project_default(
        self, session_client, workspace, project, approval_type
    ):
        link = _linked(project, approval_type).get()
        response = session_client.patch(
            LINK_URL.format(slug=workspace.slug, project_id=project.id, pk=link.id), {"is_default": True}, format="json"
        )
        _assert_refused(response)
        link.refresh_from_db()
        assert not link.is_default

    def test_a_standard_type_can_still_be_linked_and_unlinked(self, session_client, workspace, other_project, bug_type):
        response = session_client.post(
            LINKS_URL.format(slug=workspace.slug, project_id=other_project.id),
            {"issue_type_id": str(bug_type.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        link = _linked(other_project, bug_type).get()

        response = session_client.delete(LINK_URL.format(slug=workspace.slug, project_id=other_project.id, pk=link.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not _linked(other_project, bug_type).exists()

    def test_the_owning_feature_still_links_the_type(self, workspace, project, other_project, approval_type):
        assert ensure_project_kind_type(other_project, IssueTypeKind.APPROVAL) == approval_type
        assert _linked(other_project, approval_type).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectTemplate:
    def test_an_entry_named_like_a_system_managed_type_is_skipped(
        self, session_client, workspace, project, other_project, approval_type
    ):
        template = ProjectTemplate.objects.create(
            workspace=workspace,
            name="With approval",
            payload={
                "is_issue_type_enabled": True,
                "additional_work_item_types": [{"name": approval_type.name.upper()}, {"name": "Change request"}],
            },
        )
        types_before = IssueType.objects.filter(workspace=workspace).count()

        response = session_client.post(
            SEED_URL.format(slug=workspace.slug, project_id=other_project.id),
            {"template_id": str(template.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["skipped_work_item_types"] == [approval_type.name.upper()]
        assert not _linked(other_project, approval_type).exists()
        assert (
            not IssueType.objects.filter(workspace=workspace, name__iexact=approval_type.name)
            .exclude(pk=approval_type.pk)
            .exists()
        )
        # the rest of the template is applied: Task and the other entry are created and linked
        assert IssueType.objects.filter(workspace=workspace).count() == types_before + 2
        assert _linked(other_project, IssueType.objects.get(workspace=workspace, name="Change request")).exists()
        assert _linked(other_project, IssueType.objects.get(workspace=workspace, name="Task")).exists()
