# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""POST /api/v1/.../modules/<id>/module-issues/ adds work items to a module.

A work item can be in several modules, so the endpoint only adds: other modules are kept, one that is already in
the module is left as it is, and an activity is recorded for each work item that was really added.
"""

import json
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, Module, ModuleIssue, Project, ProjectMember, State

MODULE_ISSUES_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/modules/{module_id}/module-issues/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Mods", identifier="MD", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20, is_active=True)
    return project


@pytest.fixture
def issues(db, workspace, project, create_user):
    state = State.objects.create(name="Todo", project=project, group="backlog", default=True)
    result = []
    for name in ("One", "Two"):
        issue = Issue(name=name, project=project, workspace=workspace, state=state)
        issue.save(created_by_id=create_user.id)
        result.append(issue)
    return result


@pytest.fixture
def modules(db, workspace, project):
    return Module.objects.create(name="Backend", project=project, workspace=workspace), Module.objects.create(
        name="Frontend", project=project, workspace=workspace
    )


def _in_module(module):
    return {str(pk) for pk in ModuleIssue.objects.filter(module=module).values_list("issue_id", flat=True)}


def _post(client, workspace, project, module, issue_ids):
    return client.post(
        MODULE_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, module_id=module.id),
        {"issues": [str(pk) for pk in issue_ids]},
        format="json",
    )


@pytest.mark.contract
@pytest.mark.django_db
@mock.patch("plane.api.views.module.issue_activity")
def test_adding_keeps_the_other_modules(activity, api_key_client, workspace, project, issues, modules):
    backend, frontend = modules
    one, two = issues
    ModuleIssue.objects.create(module=backend, issue=one, project=project, workspace=workspace)

    response = _post(api_key_client, workspace, project, frontend, [one.id, two.id])

    assert response.status_code == status.HTTP_200_OK
    assert _in_module(frontend) == {str(one.id), str(two.id)}
    # "One" stays in the module it was in: it is not moved
    assert _in_module(backend) == {str(one.id)}


@pytest.mark.contract
@pytest.mark.django_db
@mock.patch("plane.api.views.module.issue_activity")
def test_a_work_item_already_in_the_module_is_left_alone(activity, api_key_client, workspace, project, issues, modules):
    backend, _ = modules
    one, two = issues
    ModuleIssue.objects.create(module=backend, issue=one, project=project, workspace=workspace)

    response = _post(api_key_client, workspace, project, backend, [one.id, two.id])

    assert response.status_code == status.HTTP_200_OK
    assert ModuleIssue.objects.filter(module=backend, issue=one).count() == 1
    assert _in_module(backend) == {str(one.id), str(two.id)}
    # only "Two" was added, so only "Two" has an activity
    assert [call.kwargs["issue_id"] for call in activity.delay.call_args_list] == [str(two.id)]


@pytest.mark.contract
@pytest.mark.django_db
@mock.patch("plane.api.views.module.issue_activity")
def test_each_added_work_item_gets_its_own_activity(activity, api_key_client, workspace, project, issues, modules):
    backend, _ = modules

    _post(api_key_client, workspace, project, backend, [issue.id for issue in issues])

    calls = activity.delay.call_args_list
    assert {call.kwargs["issue_id"] for call in calls} == {str(issue.id) for issue in issues}
    for call in calls:
        assert call.kwargs["type"] == "module.activity.created"
        assert json.loads(call.kwargs["requested_data"]) == {"module_id": str(backend.id)}


@pytest.mark.contract
@pytest.mark.django_db
@mock.patch("plane.api.views.module.issue_activity")
def test_a_work_item_of_another_project_is_ignored(
    activity, api_key_client, workspace, project, issues, modules, create_user
):
    backend, _ = modules
    other_project = Project.objects.create(name="Else", identifier="EL", workspace=workspace, created_by=create_user)
    other_state = State.objects.create(name="Todo", project=other_project, group="backlog", default=True)
    foreign = Issue(name="Foreign", project=other_project, workspace=workspace, state=other_state)
    foreign.save(created_by_id=create_user.id)

    response = _post(api_key_client, workspace, project, backend, [issues[0].id, foreign.id])

    assert response.status_code == status.HTTP_200_OK
    assert _in_module(backend) == {str(issues[0].id)}
