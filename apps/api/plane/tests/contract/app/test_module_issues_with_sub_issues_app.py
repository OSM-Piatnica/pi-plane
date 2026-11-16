# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Adding a work item to a module, or taking it out, together with its sub-work items.

It is a one-time copy: the flag ``include_sub_issues`` covers all descendants, not only the children, and
nothing keeps the module membership of a parent and its children in step afterwards.
"""

from unittest import mock

import pytest
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

MODULE_ISSUES_URL = "/api/workspaces/{slug}/projects/{project_id}/modules/{module_id}/issues/"
MODULE_ISSUE_URL = "/api/workspaces/{slug}/projects/{project_id}/modules/{module_id}/issues/{issue_id}/"
ISSUE_MODULES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/modules/"


def _issue(name, project, workspace, author, state, parent=None):
    issue = Issue(name=name, project=project, workspace=workspace, state=state, parent=parent)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture(autouse=True)
def _no_activity():
    with mock.patch("plane.app.views.module.issue.issue_activity"):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Mods", identifier="MD", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
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


@pytest.fixture
def module_two(db, workspace, project):
    return Module.objects.create(name="Frontend", project=project, workspace=workspace)


def _in_module(module):
    return {
        str(pk)
        for pk in ModuleIssue.objects.filter(module=module, deleted_at__isnull=True).values_list("issue_id", flat=True)
    }


@pytest.mark.contract
class TestAddWithSubIssues:
    @pytest.mark.django_db
    def test_without_the_flag_only_the_given_items_are_added(self, session_client, workspace, project, module, tree):
        response = session_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert _in_module(module) == {str(tree["epic"].id)}

    @pytest.mark.django_db
    def test_with_the_flag_all_descendants_come_along(self, session_client, workspace, project, module, tree):
        response = session_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert _in_module(module) == {str(tree[key].id) for key in ("epic", "a", "b", "g")}
        # the response names every work item that was added, so a client can update its copies
        assert set(response.data["issue_ids"]) == _in_module(module)

    @pytest.mark.django_db
    def test_items_already_in_the_module_are_kept_once(self, session_client, workspace, project, module, tree):
        ModuleIssue.objects.create(module=module, issue=tree["a"], project=project, workspace=workspace)
        session_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": "true"},
            format="json",
        )
        assert ModuleIssue.objects.filter(module=module, issue=tree["a"], deleted_at__isnull=True).count() == 1
        assert len(_in_module(module)) == 4

    @pytest.mark.django_db
    def test_archived_sub_items_are_left_out(self, session_client, workspace, project, module, tree):
        from django.utils import timezone

        Issue.objects.filter(pk=tree["b"].pk).update(archived_at=timezone.now())
        session_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert str(tree["b"].id) not in _in_module(module)
        assert str(tree["g"].id) in _in_module(module)

    @pytest.mark.django_db
    def test_a_child_of_another_project_is_never_added(
        self, session_client, workspace, project, module, tree, state, create_user
    ):
        other_project = Project.objects.create(
            name="Else", identifier="EL", workspace=workspace, created_by=create_user
        )
        other_state = State.objects.create(name="Todo", project=other_project, group="backlog", default=True)
        foreign = _issue("Foreign", other_project, workspace, create_user, other_state, parent=tree["epic"])
        session_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert str(foreign.id) not in _in_module(module)

    @pytest.mark.django_db
    def test_the_assignee_edit_rule_covers_the_sub_items(
        self, api_client, workspace, project, module, tree, create_user
    ):
        Project.objects.filter(pk=project.pk).update(is_assignee_edit_rule_enabled=True)
        member = User.objects.create(email="m@example.com", username="m@example.com", first_name="M", last_name="M")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, workspace=workspace, role=15)
        # the grandchild belongs to somebody else
        IssueAssignee.objects.create(issue=tree["g"], assignee=create_user, project=project, workspace=workspace)
        api_client.force_authenticate(user=member)
        response = api_client.post(
            MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
            {"issues": [str(tree["epic"].id)], "include_sub_issues": True},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert _in_module(module) == set()


@pytest.mark.contract
class TestIssueSideEndpoint:
    @pytest.mark.django_db
    def test_adds_and_removes_with_the_sub_items(self, session_client, workspace, project, module, module_two, tree):
        url = ISSUE_MODULES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=tree["epic"].id)
        response = session_client.post(
            url, {"modules": [str(module.id), str(module_two.id)], "include_sub_issues": True}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        everything = {str(tree[key].id) for key in ("epic", "a", "b", "g")}
        assert _in_module(module) == everything
        assert _in_module(module_two) == everything

        response = session_client.post(
            url, {"removed_modules": [str(module_two.id)], "include_sub_issues": True}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data["removed_issue_ids"]) == everything
        assert _in_module(module_two) == set()
        assert _in_module(module) == everything

    @pytest.mark.django_db
    def test_without_the_flag_only_the_item_moves(self, session_client, workspace, project, module, tree):
        session_client.post(
            ISSUE_MODULES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=tree["epic"].id),
            {"modules": [str(module.id)]},
            format="json",
        )
        assert _in_module(module) == {str(tree["epic"].id)}


@pytest.mark.contract
class TestRemoveWithSubIssues:
    @pytest.mark.django_db
    def test_removing_a_parent_can_take_its_sub_items_along(self, session_client, workspace, project, module, tree):
        for key in ("epic", "a", "b", "g", "other"):
            ModuleIssue.objects.create(module=module, issue=tree[key], project=project, workspace=workspace)
        url = MODULE_ISSUE_URL.format(
            slug=workspace.slug, project_id=project.id, module_id=module.id, issue_id=tree["epic"].id
        )
        response = session_client.delete(url + "?include_sub_issues=true")
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["issue_ids"]) == {str(tree[key].id) for key in ("epic", "a", "b", "g")}
        assert _in_module(module) == {str(tree["other"].id)}

    @pytest.mark.django_db
    def test_without_the_flag_the_children_stay(self, session_client, workspace, project, module, tree):
        for key in ("epic", "a", "g"):
            ModuleIssue.objects.create(module=module, issue=tree[key], project=project, workspace=workspace)
        response = session_client.delete(
            MODULE_ISSUE_URL.format(
                slug=workspace.slug, project_id=project.id, module_id=module.id, issue_id=tree["epic"].id
            )
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _in_module(module) == {str(tree["a"].id), str(tree["g"].id)}
