# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shifting dependents: the cause in the history, the project setting that switches the offer off, and sub-items."""

import json
from contextlib import nullcontext
from datetime import date
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import (
    Issue,
    IssueActivity,
    IssueRelation,
    Project,
    ProjectMember,
    User,
    WorkspaceMember,
)

ACTIVITY = "plane.utils.issue_reschedule.issue_activity.delay"


@pytest.fixture
def project(db, workspace, create_user):
    # These tests count calendar days, so the project has no weekend
    project = Project.objects.create(
        name="Shift", identifier="SHF", workspace=workspace, created_by=create_user, weekend_days=[]
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def other_project(db, workspace, create_user):
    project = Project.objects.create(
        name="Other", identifier="OTH", workspace=workspace, created_by=create_user, weekend_days=[]
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def item(project, name, start=None, finish=None, parent=None):
    return Issue.objects.create(
        name=name, workspace=project.workspace, project=project, start_date=start, finish_date=finish, parent=parent
    )


def relate(predecessor, successor):
    """``successor`` is blocked by ``predecessor`` (the row is stored on the successor)."""
    return IssueRelation.objects.create(
        issue=successor,
        related_issue=predecessor,
        relation_type="blocked_by",
        project=successor.project,
        workspace=successor.workspace,
    )


def issue_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def dates_url(workspace, project):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-dates/"


def public_url(workspace, project, issue):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def patch(client, workspace, project, issue, data, on_commit=None):
    """``on_commit`` is the ``django_capture_on_commit_callbacks`` fixture, for the activity entries of a shift."""
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY) as activity,
        on_commit(execute=True) if on_commit else nullcontext(),
    ):
        response = client.patch(issue_url(workspace, project, issue), data, format="json")
    return response, activity


def drag(client, workspace, project, updates, confirmed=False, on_commit=None):
    body = {"updates": updates, "shift_dependents": True} if confirmed else {"updates": updates}
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch(ACTIVITY) as activity,
        on_commit(execute=True) if on_commit else nullcontext(),
    ):
        response = client.post(dates_url(workspace, project), body, format="json")
    return response, activity


def code(response):
    """The error code of a refusal: a serializer wraps every value of its error in a list, a view does not."""
    value = response.json()["error_code"]
    return value[0] if isinstance(value, list) else value


def dates(issue):
    issue.refresh_from_db()
    return issue.start_date, issue.finish_date


def causes(activity):
    """Shifted work item id -> the ids its activity entries name as the cause."""
    found = {}
    for call in activity.call_args_list:
        found.setdefault(call.kwargs["issue_id"], set()).add(call.kwargs.get("shifted_after"))
    return found


def write_activities(activity):
    """Run the activity task for every entry the shift queued, as the worker would."""
    for call in activity.call_args_list:
        issue_activity(**call.kwargs)


@pytest.mark.contract
@pytest.mark.django_db
class TestCauseInHistory:
    def test_every_shifted_item_names_the_changed_item_also_down_the_chain(
        self, session_client, workspace, project, django_capture_on_commit_callbacks
    ):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 15))
        c = item(project, "c", date(2026, 1, 16), date(2026, 1, 20))
        relate(a, b)
        relate(b, c)

        response, activity = patch(
            session_client,
            workspace,
            project,
            a,
            {"finish_date": "2026-01-12", "shift_dependents": True},
            on_commit=django_capture_on_commit_callbacks,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # c moved because b moved, but what the person changed was a
        assert causes(activity) == {str(b.id): {str(a.id)}, str(c.id): {str(a.id)}}

    def test_a_drag_of_several_items_names_the_right_one_for_each_dependent(
        self, session_client, workspace, project, django_capture_on_commit_callbacks
    ):
        a1 = item(project, "a1", date(2026, 1, 1), date(2026, 1, 10))
        b1 = item(project, "b1", date(2026, 1, 11), date(2026, 1, 20))
        a2 = item(project, "a2", date(2026, 2, 1), date(2026, 2, 10))
        b2 = item(project, "b2", date(2026, 2, 11), date(2026, 2, 20))
        relate(a1, b1)
        relate(a2, b2)
        updates = [
            {"id": str(a1.id), "start_date": "2026-01-05", "finish_date": "2026-01-14"},
            {"id": str(a2.id), "start_date": "2026-02-05", "finish_date": "2026-02-14"},
        ]

        response, activity = drag(
            session_client, workspace, project, updates, confirmed=True, on_commit=django_capture_on_commit_callbacks
        )

        assert response.status_code == status.HTTP_200_OK
        assert causes(activity) == {str(b1.id): {str(a1.id)}, str(b2.id): {str(a2.id)}}

    def test_the_entry_names_and_links_the_cause(
        self, session_client, workspace, project, other_project, django_capture_on_commit_callbacks
    ):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        # the dependent is in another project: the cause is looked up across projects of the workspace
        b = item(other_project, "b", date(2026, 1, 11), date(2026, 1, 20))
        relate(a, b)

        response, activity = patch(
            session_client,
            workspace,
            project,
            a,
            {"finish_date": "2026-01-14", "shift_dependents": True},
            on_commit=django_capture_on_commit_callbacks,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        write_activities(activity)

        entries = {entry.field: entry for entry in IssueActivity.objects.filter(issue=b)}
        assert set(entries) == {"start_date", "finish_date"}
        ref = f"SHF-{a.sequence_id}"
        assert entries["start_date"].comment == f"moved the start date automatically after {ref} changed to"
        assert entries["finish_date"].comment == f"moved the finish date automatically after {ref} changed to"
        for entry in entries.values():
            assert entry.old_identifier == a.id
        assert entries["start_date"].new_value == "2026-01-15"

        history = session_client.get(issue_url(workspace, other_project, b) + "history/")
        assert history.status_code == status.HTTP_200_OK
        shown = [row["shift_cause"] for row in history.json() if row.get("field") in ("start_date", "finish_date")]
        cause = {
            "id": str(a.id),
            "project_id": str(project.id),
            "sequence_id": a.sequence_id,
            "project_identifier": "SHF",
        }
        assert shown == [cause, cause]

    def test_a_date_changed_by_hand_has_no_cause(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))

        issue_activity(
            type="issue.activity.updated",
            requested_data=json.dumps({"start_date": "2026-01-02"}),
            current_instance=json.dumps({"start_date": "2026-01-01"}),
            issue_id=str(a.id),
            actor_id=str(a.created_by_id) if a.created_by_id else None,
            project_id=str(project.id),
            epoch=1767225600,
        )

        entry = IssueActivity.objects.get(issue=a, field="start_date")
        assert entry.comment == "updated the start date to "
        assert entry.old_identifier is None
        history = session_client.get(issue_url(workspace, project, a) + "history/")
        assert [row["shift_cause"] for row in history.json() if row.get("field") == "start_date"] == [None]

    def test_a_cause_that_is_gone_leaves_a_plain_entry(self, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))

        issue_activity(
            type="issue.activity.updated",
            requested_data=json.dumps({"start_date": "2026-01-02"}),
            current_instance=json.dumps({"start_date": "2026-01-01"}),
            issue_id=str(a.id),
            actor_id=None,
            project_id=str(project.id),
            epoch=1767225600,
            shifted_after="00000000-0000-4000-8000-000000000000",
        )

        entry = IssueActivity.objects.get(issue=a, field="start_date")
        assert entry.comment == "updated the start date to "
        assert entry.old_identifier is None


@pytest.mark.contract
@pytest.mark.django_db
class TestForgedCause:
    """A client cannot make its own date change look like an automatic shift after another work item."""

    @pytest.fixture
    def hidden(self, workspace, create_user):
        # a work item in a project the person is not a member of
        secret = Project.objects.create(
            name="Secret", identifier="SEC", workspace=workspace, created_by=create_user, weekend_days=[]
        )
        return item(secret, "hidden", date(2026, 1, 1), date(2026, 1, 10))

    def assert_plain(self, item_, field_name):
        entry = IssueActivity.objects.get(issue=item_, field=field_name)
        assert entry.comment in ("updated the start date to ", "updated the finish date to")
        assert entry.old_identifier is None

    def run_queued(self, task_mock):
        for call in task_mock.delay.call_args_list:
            if call.kwargs.get("type") == "issue.activity.updated":
                assert "shifted_after" not in call.kwargs
                issue_activity(**call.kwargs)

    def test_app_api(self, session_client, workspace, project, hidden):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))

        with (
            mock.patch("plane.app.views.issue.base.issue_activity") as task,
            mock.patch("plane.app.views.issue.base.model_activity"),
        ):
            response = session_client.patch(
                issue_url(workspace, project, a),
                {"start_date": "2026-01-02", "finish_date": "2026-01-12", "shifted_after": str(hidden.id)},
                format="json",
            )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        self.run_queued(task)

        self.assert_plain(a, "start_date")
        self.assert_plain(a, "finish_date")
        history = session_client.get(issue_url(workspace, project, a) + "history/")
        assert {row["shift_cause"] for row in history.json() if row.get("field") in ("start_date", "finish_date")} == {
            None
        }

    def test_public_api(self, api_key_client, workspace, project, hidden):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))

        with mock.patch("plane.api.views.issue.issue_activity") as task:
            response = api_key_client.patch(
                public_url(workspace, project, a),
                {"start_date": "2026-01-02", "shifted_after": str(hidden.id)},
                format="json",
            )
        assert response.status_code == status.HTTP_200_OK, response.content
        self.run_queued(task)

        self.assert_plain(a, "start_date")

    def test_the_task_drops_a_cause_in_the_requested_data(self, workspace, project, hidden):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))

        issue_activity(
            type="issue.activity.updated",
            requested_data=json.dumps({"start_date": "2026-01-02", "shifted_after": str(hidden.id)}),
            current_instance=json.dumps({"start_date": "2026-01-01"}),
            issue_id=str(a.id),
            actor_id=None,
            project_id=str(project.id),
            epoch=1767225600,
        )

        self.assert_plain(a, "start_date")


@pytest.mark.contract
@pytest.mark.django_db
class TestOfferSwitchedOff:
    """With the project setting off, a change that breaks a relation is refused as before the offer existed."""

    @pytest.fixture
    def pair(self, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 20))
        relate(a, b)
        return a, b

    @pytest.fixture
    def switched_off(self, project):
        Project.objects.filter(pk=project.pk).update(is_reschedule_offer_enabled=False)

    def test_the_offer_is_on_by_default(self, project):
        assert project.is_reschedule_offer_enabled is True

    def test_a_project_admin_switches_it_off(self, session_client, workspace, project):
        with mock.patch("plane.app.views.project.base.model_activity"):
            response = session_client.patch(
                f"/api/workspaces/{workspace.slug}/projects/{project.id}/",
                {"is_reschedule_offer_enabled": False},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK, response.data
        project.refresh_from_db()
        assert project.is_reschedule_offer_enabled is False

    def test_a_member_who_is_not_an_admin_cannot_switch_it(self, workspace, project):
        member = User.objects.create(email="member@example.com", username="member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, role=15, is_active=True)
        client = APIClient()
        client.force_authenticate(user=member)

        with mock.patch("plane.app.views.project.base.model_activity"):
            response = client.patch(
                f"/api/workspaces/{workspace.slug}/projects/{project.id}/",
                {"is_reschedule_offer_enabled": False},
                format="json",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        project.refresh_from_db()
        assert project.is_reschedule_offer_enabled is True

    @pytest.mark.parametrize("confirmed", [False, True])
    def test_app_update_is_refused(self, session_client, workspace, project, pair, switched_off, confirmed):
        a, b = pair
        data = {"finish_date": "2026-01-14", **({"shift_dependents": True} if confirmed else {})}

        response, activity = patch(session_client, workspace, project, a, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"
        assert "shifts" not in response.json()
        activity.assert_not_called()
        assert dates(a) == (date(2026, 1, 1), date(2026, 1, 10))
        assert dates(b) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_app_update_is_offered_when_on(self, session_client, workspace, project, pair):
        a, _ = pair

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_reschedule_available"

    @pytest.mark.parametrize("confirmed", [False, True])
    def test_timeline_drag_is_refused(self, session_client, workspace, project, pair, switched_off, confirmed):
        a, b = pair
        update = {"id": str(a.id), "start_date": "2026-01-05", "finish_date": "2026-01-14"}

        response, activity = drag(session_client, workspace, project, [update], confirmed=confirmed)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"
        assert "shifts" not in response.json()
        activity.assert_not_called()
        assert dates(a) == (date(2026, 1, 1), date(2026, 1, 10))
        assert dates(b) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_timeline_drag_is_offered_when_on(self, session_client, workspace, project, pair):
        a, _ = pair
        update = {"id": str(a.id), "start_date": "2026-01-05", "finish_date": "2026-01-14"}

        response, _ = drag(session_client, workspace, project, [update])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_reschedule_available"

    @pytest.mark.parametrize("confirmed", [False, True])
    def test_public_api_update_is_refused(self, api_key_client, workspace, project, pair, switched_off, confirmed):
        a, b = pair
        data = {"finish_date": "2026-01-14", **({"shift_dependents": True} if confirmed else {})}

        with mock.patch(ACTIVITY) as activity:
            response = api_key_client.patch(public_url(workspace, project, a), data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"
        assert "shifts" not in response.json()
        activity.assert_not_called()
        assert dates(a) == (date(2026, 1, 1), date(2026, 1, 10))
        assert dates(b) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_public_api_update_is_offered_when_on(self, api_key_client, workspace, project, pair):
        a, _ = pair

        with mock.patch(ACTIVITY):
            response = api_key_client.patch(
                public_url(workspace, project, a), {"finish_date": "2026-01-14"}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_reschedule_available"

    def test_the_project_of_the_changed_item_decides(self, session_client, workspace, project, other_project):
        # the dependent's project has the offer off, the changed item's project has it on: offered
        Project.objects.filter(pk=other_project.pk).update(is_reschedule_offer_enabled=False)
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        elsewhere = item(other_project, "elsewhere", date(2026, 1, 11), date(2026, 1, 20))
        relate(a, elsewhere)

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert code(response) == "relation_reschedule_available"

        # and the other way round: refused
        back = item(other_project, "back", date(2026, 3, 1), date(2026, 3, 10))
        here = item(project, "here", date(2026, 3, 11), date(2026, 3, 20))
        relate(back, here)

        response, _ = patch(session_client, workspace, other_project, back, {"finish_date": "2026-03-14"})

        assert code(response) == "relation_date_conflict"

    def test_a_change_that_breaks_nothing_still_goes_through(
        self, session_client, workspace, project, pair, switched_off
    ):
        a, _ = pair

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-09"})

        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.contract
@pytest.mark.django_db
class TestSubItems:
    """What a shift does around a parent and its sub-items.

    The dates rolled up from sub-items are only drawn on the timeline: a parent keeps its own stored dates, and
    relations are checked against those. Sub-items do not inherit the relations of their parent. These tests pin that
    behaviour down; see docs/working-days.md.
    """

    def rollup(self, client, workspace, project, parent):
        response = client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-date-rollups/",
            {"issue_ids": str(parent.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        return response.json()[str(parent.id)]

    def test_moving_a_parent_shifts_its_successors_and_leaves_its_sub_items(self, session_client, workspace, project):
        parent = item(project, "parent", date(2026, 1, 1), date(2026, 1, 10))
        child = item(project, "child", date(2026, 1, 3), date(2026, 1, 8), parent=parent)
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(parent, successor)

        offered, _ = patch(
            session_client,
            workspace,
            project,
            parent,
            {"start_date": "2026-01-05", "finish_date": "2026-01-14"},
        )
        assert code(offered) == "relation_reschedule_available"
        # only the successor is in the offer: the sub-item is not
        assert [shift["id"] for shift in offered.json()["shifts"]] == [str(successor.id)]

        response, _ = patch(
            session_client,
            workspace,
            project,
            parent,
            {"start_date": "2026-01-05", "finish_date": "2026-01-14", "shift_dependents": True},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(successor) == (date(2026, 1, 15), date(2026, 1, 24))
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

    def test_a_parent_shifted_as_a_dependent_takes_its_successors_but_not_its_sub_items(
        self, session_client, workspace, project
    ):
        first = item(project, "first", date(2026, 1, 1), date(2026, 1, 10))
        parent = item(project, "parent", date(2026, 1, 11), date(2026, 1, 20))
        child = item(project, "child", date(2026, 1, 11), date(2026, 1, 20), parent=parent)
        after_parent = item(project, "after parent", date(2026, 1, 21), date(2026, 1, 25))
        relate(first, parent)
        relate(parent, after_parent)

        response, _ = patch(
            session_client, workspace, project, first, {"finish_date": "2026-01-14", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(parent) == (date(2026, 1, 15), date(2026, 1, 24))
        assert dates(after_parent) == (date(2026, 1, 25), date(2026, 1, 29))
        # the sub-item stays where it was, now before its parent starts
        assert dates(child) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_a_sub_item_that_outgrows_its_parent_moves_neither_the_parent_nor_its_successors(
        self, session_client, workspace, project
    ):
        parent = item(project, "parent", date(2026, 1, 1), date(2026, 1, 10))
        child = item(project, "child", date(2026, 1, 3), date(2026, 1, 8), parent=parent)
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(parent, successor)

        # nothing depends on the sub-item itself, so there is no conflict and nothing to offer
        response, activity = patch(session_client, workspace, project, child, {"finish_date": "2026-01-18"})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        activity.assert_not_called()
        assert dates(parent) == (date(2026, 1, 1), date(2026, 1, 10))
        assert dates(successor) == (date(2026, 1, 11), date(2026, 1, 20))
        # the timeline now draws the sub-items past the parent's own end and past the successor's start
        assert self.rollup(session_client, workspace, project, parent)["target_date"] == "2026-01-18"

    def test_a_parent_without_dates_of_its_own_holds_nothing_back(self, session_client, workspace, project):
        # drawn on the timeline from its sub-items' dates, but the relation has no date of the parent to check
        parent = item(project, "parent")
        child = item(project, "child", date(2026, 1, 1), date(2026, 1, 10), parent=parent)
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(parent, successor)

        response, activity = patch(session_client, workspace, project, child, {"finish_date": "2026-01-18"})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        activity.assert_not_called()
        assert dates(successor) == (date(2026, 1, 11), date(2026, 1, 20))
        assert self.rollup(session_client, workspace, project, parent)["target_date"] == "2026-01-18"

    def test_a_sub_item_shifted_as_a_dependent_leaves_its_parent(self, session_client, workspace, project):
        first = item(project, "first", date(2026, 1, 1), date(2026, 1, 10))
        parent = item(project, "parent", date(2026, 1, 11), date(2026, 1, 20))
        child = item(project, "child", date(2026, 1, 11), date(2026, 1, 20), parent=parent)
        relate(first, child)

        response, _ = patch(
            session_client, workspace, project, first, {"finish_date": "2026-01-14", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 15), date(2026, 1, 24))
        assert dates(parent) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_sub_items_do_not_inherit_the_predecessors_of_their_parent(self, session_client, workspace, project):
        first = item(project, "first", date(2026, 1, 1), date(2026, 1, 10))
        parent = item(project, "parent", date(2026, 1, 11), date(2026, 1, 20))
        child = item(project, "child", date(2026, 1, 11), date(2026, 1, 20), parent=parent)
        relate(first, parent)

        # the parent may not start before the 11th, its sub-item may
        refused, _ = patch(session_client, workspace, project, parent, {"start_date": "2026-01-05"})
        allowed, _ = patch(session_client, workspace, project, child, {"start_date": "2026-01-05"})

        assert refused.status_code == status.HTTP_400_BAD_REQUEST
        assert code(refused) == "relation_date_conflict"
        assert allowed.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 5), date(2026, 1, 20))
