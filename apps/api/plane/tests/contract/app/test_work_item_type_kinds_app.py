# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the kinds of work item types.

The kind of a type decides where a work item can sit in the hierarchy (an Epic has no parent, a review is only a
child of an approval, a child's level is never above its parent's), whether its type can be switched by a user
(not into or out of approval and review) and whether it counts in progress (Epics and reviews do not).
"""

import pytest
from rest_framework import status

from plane.db.models import (
    Issue,
    IssueType,
    IssueTypeKind,
    Module,
    ModuleIssue,
    Project,
    ProjectIssueType,
    ProjectMember,
    State,
)
from plane.utils.project_issue_types import SYSTEM_MANAGED_TYPE_CODE, IssueTypeChangeRejected
from plane.utils.work_item_hierarchy import parent_kind_error

ISSUES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"
ISSUE_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
PUBLIC_ISSUE_URL = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
SUB_ISSUES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/sub-issues/"
ISSUE_TYPES_URL = "/api/workspaces/{slug}/issue-types/"
ISSUE_TYPE_URL = "/api/workspaces/{slug}/issue-types/{pk}/"
EPICS_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-types/epics/"
MODULES_URL = "/api/workspaces/{slug}/projects/{project_id}/modules/"

KINDS = list(IssueTypeKind.values)
# "none" is a work item without a type: it behaves like the standard kind
PARENT_KINDS = [*KINDS, "none"]


def allowed(parent_kind: str, child_kind: str) -> bool:
    """The table of the plan, written out: which child kind can sit under which parent kind."""

    if child_kind == "epic":
        return False
    if child_kind == "review":
        return parent_kind == "approval"
    return parent_kind != "review"


def _make_issue(name, project, workspace, author, parent=None, issue_type=None, state=None):
    issue = Issue(name=name, project=project, workspace=workspace, parent=parent, type=issue_type, state=state)
    issue.save(created_by_id=author.id)
    return issue


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Kinds", identifier="KD", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def types(db, workspace, project):
    """One linked type per kind, and a second standard type; `none` stands for a work item without a type."""

    made = {kind: IssueType.objects.create(workspace=workspace, name=f"{kind} type", kind=kind) for kind in KINDS}
    made["bug"] = IssueType.objects.create(workspace=workspace, name="Bug")
    for issue_type in made.values():
        ProjectIssueType.objects.create(project=project, issue_type=issue_type, workspace=workspace)
    made["none"] = None
    return made


@pytest.mark.contract
class TestHierarchyMatrix:
    @pytest.mark.parametrize("child_kind", KINDS)
    @pytest.mark.parametrize("parent_kind", PARENT_KINDS)
    def test_the_rule_table(self, parent_kind, child_kind):
        error = parent_kind_error(child_kind, "standard" if parent_kind == "none" else parent_kind)
        assert (error is None) is allowed(parent_kind, child_kind)

    @pytest.mark.parametrize("child_kind", KINDS)
    def test_only_a_review_needs_a_parent(self, child_kind):
        assert (parent_kind_error(child_kind, None) is None) is (child_kind != "review")

    @pytest.mark.django_db
    @pytest.mark.parametrize("child_kind", [*KINDS, "none"])
    @pytest.mark.parametrize("parent_kind", PARENT_KINDS)
    def test_setting_a_parent(self, session_client, workspace, project, types, create_user, parent_kind, child_kind):
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        parent = _make_issue("Parent", project, workspace, create_user, issue_type=types[parent_kind])
        # A review starts under an approval, as the system makes it; every other kind starts without a parent
        first_parent = approval if child_kind == "review" else None
        child = _make_issue("Child", project, workspace, create_user, parent=first_parent, issue_type=types[child_kind])

        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=child.id),
            {"parent_id": str(parent.id)},
            format="json",
        )

        child.refresh_from_db()
        if allowed(parent_kind, "standard" if child_kind == "none" else child_kind):
            assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
            assert child.parent_id == parent.id
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "parent_id" in response.data
            assert child.parent_id == (first_parent.id if first_parent else None)

    @pytest.mark.django_db
    @pytest.mark.parametrize("child_kind", KINDS)
    @pytest.mark.parametrize("parent_kind", PARENT_KINDS)
    def test_attaching_a_sub_work_item(
        self, session_client, workspace, project, types, create_user, parent_kind, child_kind
    ):
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        parent = _make_issue("Parent", project, workspace, create_user, issue_type=types[parent_kind])
        first_parent = approval if child_kind == "review" else None
        child = _make_issue("Child", project, workspace, create_user, parent=first_parent, issue_type=types[child_kind])

        response = session_client.post(
            SUB_ISSUES_URL.format(slug=workspace.slug, project_id=project.id, issue_id=parent.id),
            {"sub_issue_ids": [str(child.id)]},
            format="json",
        )

        child.refresh_from_db()
        if allowed(parent_kind, child_kind):
            assert response.status_code == status.HTTP_200_OK, response.data
            assert child.parent_id == parent.id
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert child.parent_id == (first_parent.id if first_parent else None)

    @pytest.mark.django_db
    def test_a_review_cannot_lose_its_parent(self, session_client, workspace, project, types, create_user):
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        review = _make_issue("Review", project, workspace, create_user, parent=approval, issue_type=types["review"])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=review.id),
            {"parent_id": None},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parent_id" in response.data
        review.refresh_from_db()
        assert review.parent_id == approval.id

    @pytest.mark.django_db
    def test_a_review_cannot_be_created_without_an_approval_parent(
        self, session_client, workspace, project, types, create_user
    ):
        State.objects.create(name="Todo", project=project, group="unstarted", default=True)
        url = ISSUES_URL.format(slug=workspace.slug, project_id=project.id)
        task = _make_issue("Task", project, workspace, create_user, issue_type=types["standard"])
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])

        alone = session_client.post(url, {"name": "Alone", "type_id": str(types["review"].id)}, format="json")
        assert alone.status_code == status.HTTP_400_BAD_REQUEST
        under_task = session_client.post(
            url, {"name": "Under task", "type_id": str(types["review"].id), "parent_id": str(task.id)}, format="json"
        )
        assert under_task.status_code == status.HTTP_400_BAD_REQUEST
        assert not Issue.objects.filter(project=project, type=types["review"]).exists()

        under_approval = session_client.post(
            url,
            {"name": "Step", "type_id": str(types["review"].id), "parent_id": str(approval.id)},
            format="json",
        )
        assert under_approval.status_code == status.HTTP_201_CREATED, under_approval.data
        assert Issue.objects.get(project=project, name="Step").parent_id == approval.id

    @pytest.mark.django_db
    def test_renaming_a_review_does_not_run_the_parent_rules(
        self, session_client, workspace, project, types, create_user
    ):
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        review = _make_issue("Review", project, workspace, create_user, parent=approval, issue_type=types["review"])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=review.id),
            {"name": "Legal review"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data


@pytest.mark.contract
class TestTypeSwitch:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current,new",
        [
            ("standard", "approval"),
            ("standard", "review"),
            ("none", "approval"),
            ("none", "review"),
            ("epic", "approval"),
            ("approval", "standard"),
            ("approval", "milestone"),
            ("approval", "review"),
        ],
    )
    def test_switching_into_or_out_of_a_system_managed_kind_is_rejected(
        self, session_client, workspace, project, types, create_user, current, new
    ):
        item = _make_issue("Item", project, workspace, create_user, issue_type=types[current])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"type_id": str(types[new].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_code"] == SYSTEM_MANAGED_TYPE_CODE
        assert response.data["error"]
        item.refresh_from_db()
        assert item.type_id == (types[current].id if types[current] else None)

    @pytest.mark.django_db
    def test_a_review_cannot_become_a_task(self, session_client, workspace, project, types, create_user):
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        review = _make_issue("Review", project, workspace, create_user, parent=approval, issue_type=types["review"])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=review.id),
            {"type_id": str(types["standard"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_code"] == SYSTEM_MANAGED_TYPE_CODE
        review.refresh_from_db()
        assert review.type_id == types["review"].id

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current,new", [("standard", "bug"), ("standard", "milestone"), ("standard", "epic"), ("none", "standard")]
    )
    def test_other_switches_still_work(self, session_client, workspace, project, types, create_user, current, new):
        item = _make_issue("Item", project, workspace, create_user, issue_type=types[current])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"type_id": str(types[new].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        item.refresh_from_db()
        assert item.type_id == types[new].id

    @pytest.mark.django_db
    def test_sending_the_same_system_managed_type_is_fine(self, session_client, workspace, project, types, create_user):
        item = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"type_id": str(types["approval"].id), "name": "Sign-off"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data

    @pytest.mark.django_db
    def test_a_new_work_item_can_be_an_approval(self, session_client, workspace, project, types):
        State.objects.create(name="Todo", project=project, group="unstarted", default=True)
        response = session_client.post(
            ISSUES_URL.format(slug=workspace.slug, project_id=project.id),
            {"name": "Sign-off", "type_id": str(types["approval"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Issue.objects.get(project=project, name="Sign-off").type_id == types["approval"].id

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["approval", "review"])
    def test_clearing_the_type_of_a_system_managed_item_is_rejected(
        self, session_client, workspace, project, types, create_user, kind
    ):
        # Taking the type off would open the way round the rule: null first, then any standard type
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        item = (
            approval
            if kind == "approval"
            else _make_issue("Review", project, workspace, create_user, parent=approval, issue_type=types["review"])
        )
        url = ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id)

        cleared = session_client.patch(url, {"type_id": None}, format="json")

        assert cleared.status_code == status.HTTP_400_BAD_REQUEST
        assert cleared.data["error_code"] == SYSTEM_MANAGED_TYPE_CODE
        item.refresh_from_db()
        assert item.type_id == types[kind].id
        # The second step of the way round is refused as well, since the type is still there
        switched = session_client.patch(url, {"type_id": str(types["standard"].id)}, format="json")
        assert switched.status_code == status.HTTP_400_BAD_REQUEST
        item.refresh_from_db()
        assert item.type_id == types[kind].id

    @pytest.mark.django_db
    def test_clearing_the_type_of_other_items_still_works(self, session_client, workspace, project, types, create_user):
        for name, kind in (("Task", "standard"), ("Milestone", "milestone"), ("Untyped", "none")):
            item = _make_issue(name, project, workspace, create_user, issue_type=types[kind])
            response = session_client.patch(
                ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
                {"type_id": None},
                format="json",
            )
            assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
            item.refresh_from_db()
            assert item.type_id is None

    @pytest.mark.django_db
    def test_a_patch_without_a_type_leaves_a_system_managed_item_alone(
        self, session_client, workspace, project, types, create_user
    ):
        item = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        response = session_client.patch(
            ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"priority": "high"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        item.refresh_from_db()
        assert item.type_id == types["approval"].id

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["approval", "review"])
    def test_the_public_api_rejects_clearing_the_type(
        self, api_key_client, workspace, project, types, create_user, kind
    ):
        from plane.api.serializers import IssueSerializer

        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        item = (
            approval
            if kind == "approval"
            else _make_issue("Review", project, workspace, create_user, parent=approval, issue_type=types["review"])
        )
        context = {"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None}

        serializer = IssueSerializer(item, data={"type_id": None}, partial=True, context=context)
        with pytest.raises(IssueTypeChangeRejected) as rejected:
            serializer.is_valid()
        assert rejected.value.detail["error_code"] == SYSTEM_MANAGED_TYPE_CODE

        response = api_key_client.patch(
            PUBLIC_ISSUE_URL.format(slug=workspace.slug, project_id=project.id, issue_id=item.id),
            {"type_id": None},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        assert response.data["error_code"] == SYSTEM_MANAGED_TYPE_CODE
        item.refresh_from_db()
        assert item.type_id == types[kind].id

    @pytest.mark.django_db
    def test_the_public_api_still_clears_the_type_of_a_task(self, workspace, project, types, create_user):
        from plane.api.serializers import IssueSerializer

        context = {"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None}
        task = _make_issue("Task", project, workspace, create_user, issue_type=types["standard"])
        serializer = IssueSerializer(task, data={"type_id": None}, partial=True, context=context)
        assert serializer.is_valid(), serializer.errors
        # A patch that does not send the type is not a change of type
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])
        untouched = IssueSerializer(approval, data={"name": "Sign-off"}, partial=True, context=context)
        assert untouched.is_valid(), untouched.errors

    @pytest.mark.django_db
    def test_the_public_api_rejects_the_switch_too(self, workspace, project, types, create_user):
        from plane.api.serializers import IssueSerializer

        context = {"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None}
        task = _make_issue("Task", project, workspace, create_user, issue_type=types["standard"])
        approval = _make_issue("Approval", project, workspace, create_user, issue_type=types["approval"])

        for item, new in ((task, "approval"), (approval, "standard")):
            serializer = IssueSerializer(item, data={"type_id": str(types[new].id)}, partial=True, context=context)
            with pytest.raises(IssueTypeChangeRejected) as rejected:
                serializer.is_valid()
            assert rejected.value.detail["error_code"] == SYSTEM_MANAGED_TYPE_CODE
            assert rejected.value.status_code == status.HTTP_400_BAD_REQUEST

        allowed_switch = IssueSerializer(task, data={"type_id": str(types["bug"].id)}, partial=True, context=context)
        assert allowed_switch.is_valid(), allowed_switch.errors


@pytest.mark.contract
class TestKindInTheTypeApi:
    @pytest.mark.django_db
    def test_kind_is_listed(self, session_client, workspace, project, types):
        response = session_client.get(ISSUE_TYPES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        kinds = {row["name"]: row["kind"] for row in rows}
        assert kinds["approval type"] == "approval"
        assert kinds["epic type"] == "epic"
        assert kinds["Bug"] == "standard"
        assert {row["name"] for row in rows if row["is_epic"]} == {"epic type"}

    @pytest.mark.django_db
    def test_kind_cannot_be_written(self, session_client, workspace, project, types):
        created = session_client.post(
            ISSUE_TYPES_URL.format(slug=workspace.slug), {"name": "Sneaky", "kind": "approval"}, format="json"
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert created.data["kind"] == "standard"

        patched = session_client.patch(
            ISSUE_TYPE_URL.format(slug=workspace.slug, pk=types["bug"].id), {"kind": "review"}, format="json"
        )
        assert patched.status_code == status.HTTP_200_OK, patched.data
        types["bug"].refresh_from_db()
        assert types["bug"].kind == "standard"

    @pytest.mark.django_db
    def test_the_is_epic_flag_moves_the_kind(self, session_client, workspace, project, types):
        url = ISSUE_TYPE_URL.format(slug=workspace.slug, pk=types["bug"].id)
        on = session_client.patch(url, {"is_epic": True}, format="json")
        assert on.status_code == status.HTTP_200_OK, on.data
        assert (on.data["kind"], on.data["is_epic"]) == ("epic", True)
        off = session_client.patch(url, {"is_epic": False}, format="json")
        assert off.status_code == status.HTTP_200_OK, off.data
        assert (off.data["kind"], off.data["is_epic"]) == ("standard", False)

    @pytest.mark.django_db
    def test_a_new_type_with_the_flag_is_an_epic(self, session_client, workspace, project):
        created = session_client.post(
            ISSUE_TYPES_URL.format(slug=workspace.slug), {"name": "Theme", "is_epic": True}, format="json"
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert (created.data["kind"], created.data["is_epic"]) == ("epic", True)

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["milestone", "approval", "review"])
    def test_the_flag_is_refused_on_the_other_kinds(self, session_client, workspace, project, types, kind):
        response = session_client.patch(
            ISSUE_TYPE_URL.format(slug=workspace.slug, pk=types[kind].id), {"is_epic": True}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_epic" in response.data
        types[kind].refresh_from_db()
        assert (types[kind].kind, types[kind].is_epic) == (kind, False)

    @pytest.mark.django_db
    def test_the_epics_switch_answers_with_the_epic_kind(self, session_client, workspace, project):
        response = session_client.post(EPICS_URL.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert (response.data["kind"], response.data["is_epic"]) == ("epic", True)


@pytest.mark.contract
class TestProgress:
    @pytest.mark.django_db
    def test_reviews_and_epics_do_not_count_in_a_module(self, session_client, workspace, project, types, create_user):
        states = {
            group: State.objects.create(name=group, project=project, group=group, default=(group == "backlog"))
            for group in ("backlog", "started", "completed")
        }
        module = Module.objects.create(name="Release", project=project, workspace=workspace)
        epic = _make_issue("Epic", project, workspace, create_user, issue_type=types["epic"], state=states["started"])
        approval = _make_issue(
            "Approval",
            project,
            workspace,
            create_user,
            parent=epic,
            issue_type=types["approval"],
            state=states["started"],
        )
        steps = [
            _make_issue(
                f"Step {n}",
                project,
                workspace,
                create_user,
                parent=approval,
                issue_type=types["review"],
                state=states["completed"],
            )
            for n in range(3)
        ]
        task = _make_issue(
            "Task", project, workspace, create_user, issue_type=types["standard"], state=states["completed"]
        )
        milestone = _make_issue(
            "Milestone", project, workspace, create_user, issue_type=types["milestone"], state=states["backlog"]
        )
        for issue in (epic, approval, *steps, task, milestone):
            ModuleIssue.objects.create(module=module, issue=issue, project=project, workspace=workspace)

        response = session_client.get(MODULES_URL.format(slug=workspace.slug, project_id=project.id))

        assert response.status_code == status.HTTP_200_OK
        rows = (
            response.data["results"]
            if isinstance(response.data, dict) and "results" in response.data
            else response.data
        )
        row = next(row for row in rows if row["name"] == "Release")
        # approval, task, milestone: the Epic and the three review steps are left out
        assert row["total_issues"] == 3
        assert row["completed_issues"] == 1
        assert row["started_issues"] == 1
        assert row["backlog_issues"] == 1
