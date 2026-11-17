# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The public API can add or remove a work item together with its sub-work items (``include_sub_issues``).

Same one-time copy as the app: all descendants of the same project, nothing keeps them in step afterwards.
The flag is off by default, so existing integrations see no change.
"""

from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueAssignee,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

MODULE_ISSUES_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/modules/{module_id}/module-issues/"
MODULE_ISSUE_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/modules/{module_id}/module-issues/{issue_id}/"


def _issue(name, project, workspace, author, state, parent=None):
    issue = Issue(name=name, project=project, workspace=workspace, state=state, parent=parent)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture(autouse=True)
def _no_activity():
    with mock.patch("plane.api.views.module.issue_activity"):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Mods", identifier="MD", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20, is_active=True)
    return project


@pytest.fixture
def state(db, project):
    return State.objects.create(name="Todo", project=project, group="backlog", default=True)


@pytest.fixture
def tree(db, workspace, project, state, create_user):
    """epic > child_a > grandchild, epic > child_b, and an unrelated item"""
    epic = _issue("Epic", project, workspace, create_user, state)
    child_a = _issue("Child A", project, workspace, create_user, state, parent=epic)
    child_b = _issue("Child B", project, workspace, create_user, state, parent=epic)
    grandchild = _issue("Grandchild", project, workspace, create_user, state, parent=child_a)
    other = _issue("Other", project, workspace, create_user, state)
    return {"epic": epic, "a": child_a, "b": child_b, "g": grandchild, "other": other}


@pytest.fixture
def module(db, workspace, project):
    return Module.objects.create(name="Backend", project=project, workspace=workspace)


def _in_module(module):
    return {
        str(pk)
        for pk in ModuleIssue.objects.filter(module=module, deleted_at__isnull=True).values_list("issue_id", flat=True)
    }


def _family(tree):
    return {str(tree[key].id) for key in ("epic", "a", "b", "g")}


@pytest.mark.contract
class TestAddWithSubIssues:
    @pytest.mark.django_db
    def test_off_by_default(self, api_key_client, workspace, project, module, tree):
        response = api_key_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert _in_module(module) == {str(tree["epic"].id)}

    @pytest.mark.django_db
    def test_all_descendants_come_along(self, api_key_client, workspace, project, module, tree):
        response = api_key_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert _in_module(module) == _family(tree)

    @pytest.mark.django_db
    def test_archived_sub_items_are_left_out(self, api_key_client, workspace, project, module, tree):
        Issue.objects.filter(pk=tree["b"].pk).update(archived_at=timezone.now())
        api_key_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert str(tree["b"].id) not in _in_module(module)
        assert str(tree["g"].id) in _in_module(module)

    @pytest.mark.django_db
    def test_a_child_of_another_project_is_never_added(
        self, api_key_client, workspace, project, module, tree, create_user
    ):
        other_project = Project.objects.create(
            name="Else", identifier="EL", workspace=workspace, created_by=create_user
        )
        other_state = State.objects.create(name="Todo", project=other_project, group="backlog", default=True)
        foreign = _issue("Foreign", other_project, workspace, create_user, other_state, parent=tree["epic"])
        api_key_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert str(foreign.id) not in _in_module(module)

    @pytest.mark.django_db
    def test_the_assignee_edit_rule_covers_the_sub_items(
        self, api_client, workspace, project, module, tree, create_user
    ):
        from plane.db.models import APIToken

        Project.objects.filter(pk=project.pk).update(is_assignee_edit_rule_enabled=True)
        member = User.objects.create(email="m@example.com", username="m@example.com", first_name="M", last_name="M")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, workspace=workspace, role=15, is_active=True)
        # the grandchild belongs to somebody else
        IssueAssignee.objects.create(issue=tree["g"], assignee=create_user, project=project, workspace=workspace)
        token = APIToken.objects.create(user=member, label="member", token="member-token-123")
        api_client.credentials(HTTP_X_API_KEY=token.token)
        response = api_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert _in_module(module) == set()


@pytest.mark.contract
class TestRemoveWithSubIssues:
    @pytest.mark.django_db
    def test_the_sub_items_leave_with_the_parent(self, api_key_client, workspace, project, module, tree):
        for key in ("epic", "a", "b", "g", "other"):
            ModuleIssue.objects.create(module=module, issue=tree[key], project=project, workspace=workspace)
        response = api_key_client.delete(
            MODULE_ISSUE_URL.format(
                slug=workspace.slug, project_id=project.id, module_id=module.id, issue_id=tree["epic"].id
            )
            + "?include_sub_issues=true"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _in_module(module) == {str(tree["other"].id)}

    @pytest.mark.django_db
    def test_without_the_flag_the_children_stay(self, api_key_client, workspace, project, module, tree):
        for key in ("epic", "a", "g"):
            ModuleIssue.objects.create(module=module, issue=tree[key], project=project, workspace=workspace)
        response = api_key_client.delete(
            MODULE_ISSUE_URL.format(
                slug=workspace.slug, project_id=project.id, module_id=module.id, issue_id=tree["epic"].id
            )
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _in_module(module) == {str(tree["a"].id), str(tree["g"].id)}
