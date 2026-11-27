# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sub-items following a moved parent, and a parent counting with its sub-items' dates (decision 15, D8c).

The projects have no weekend, so a working day is a calendar day; the working-day counting has its unit tests.
"""

from contextlib import nullcontext
from datetime import date
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueRelation,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

ACTIVITY = "plane.utils.issue_reschedule.issue_activity.delay"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Follow", identifier="FOL", workspace=workspace, created_by=create_user, weekend_days=[]
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def item(project, name, start=None, finish=None, parent=None, state=None):
    return Issue.objects.create(
        name=name,
        workspace=project.workspace,
        project=project,
        start_date=start,
        finish_date=finish,
        parent=parent,
        state=state,
    )


def relate(predecessor, successor):
    """``successor`` is blocked by ``predecessor``, stored without the date check (as data from before D8c)."""
    return IssueRelation.objects.create(
        issue=successor,
        related_issue=predecessor,
        relation_type="blocked_by",
        project=successor.project,
        workspace=successor.workspace,
    )


def issue_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def patch(client, workspace, project, issue, data, on_commit=None):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY) as activity,
        on_commit(execute=True) if on_commit else nullcontext(),
    ):
        response = client.patch(issue_url(workspace, project, issue), data, format="json")
    return response, activity


def drag(client, workspace, project, body):
    with mock.patch("plane.app.views.issue.base.issue_activity"), mock.patch(ACTIVITY):
        return client.post(f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-dates/", body, format="json")


def value(response, key):
    """A value of a refusal: a serializer wraps every value of its error in a list, a view does not."""
    found = response.json()[key]
    return found[0] if isinstance(found, list) else found


def dates(issue):
    issue.refresh_from_db()
    return issue.start_date, issue.finish_date


def offered(response, key="sub_items"):
    return [(shift["id"], shift["new_start_date"], shift["new_finish_date"]) for shift in response.json()[key]]


@pytest.fixture
def family(project):
    """A parent from the 1st to the 10th with a sub-item from the 3rd to the 8th, and nothing depending on them."""
    parent = item(project, "parent", date(2026, 1, 1), date(2026, 1, 10))
    child = item(project, "child", date(2026, 1, 3), date(2026, 1, 8), parent=parent)
    return parent, child


MOVED = {"start_date": "2026-01-05", "finish_date": "2026-01-14"}


@pytest.mark.contract
@pytest.mark.django_db
class TestFollowingAParentMovedByHand:
    def test_asked_the_sub_items_alone_are_offered(self, session_client, workspace, project, family):
        parent, child = family

        response, activity = patch(session_client, workspace, project, parent, {**MOVED, "offer_sub_items": True})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert value(response, "error_code") == "relation_reschedule_available"
        assert response.json()["original_error_code"] is None
        assert response.json()["shifts"] == []
        assert offered(response) == [(str(child.id), "2026-01-07", "2026-01-12")]
        activity.assert_not_called()
        assert dates(parent) == (date(2026, 1, 1), date(2026, 1, 10))

    def test_a_client_that_does_not_ask_saves_the_parent_alone(self, session_client, workspace, project, family):
        parent, child = family

        response, activity = patch(session_client, workspace, project, parent, MOVED)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        activity.assert_not_called()
        assert dates(parent) == (date(2026, 1, 5), date(2026, 1, 14))
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

    def test_ticked_they_move_and_the_history_names_the_parent(
        self, session_client, workspace, project, family, django_capture_on_commit_callbacks
    ):
        parent, child = family

        response, activity = patch(
            session_client,
            workspace,
            project,
            parent,
            {**MOVED, "move_sub_items": True},
            on_commit=django_capture_on_commit_callbacks,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 7), date(2026, 1, 12))
        assert {call.kwargs["issue_id"] for call in activity.call_args_list} == {str(child.id)}
        assert {call.kwargs["shifted_after"] for call in activity.call_args_list} == {str(parent.id)}

    def test_not_ticked_they_stay(self, session_client, workspace, project, family):
        parent, child = family

        response, _ = patch(session_client, workspace, project, parent, {**MOVED, "move_sub_items": False})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

    def test_changing_only_the_finish_offers_nothing(self, session_client, workspace, project, family):
        parent, child = family

        response, _ = patch(
            session_client, workspace, project, parent, {"finish_date": "2026-01-20", "offer_sub_items": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

    def test_sub_items_at_any_depth_follow_and_closed_ones_stay(self, session_client, workspace, project, family):
        parent, child = family
        # a default state first, or a new work item without one would be put in the only state there is
        State.objects.create(name="Todo", project=project, workspace=project.workspace, group="unstarted", default=True)
        done = State.objects.create(name="Done", project=project, workspace=project.workspace, group="completed")
        grandchild = item(project, "grandchild", date(2026, 1, 4), date(2026, 1, 6), parent=child)
        finished = item(project, "finished", date(2026, 1, 2), date(2026, 1, 3), parent=parent, state=done)

        response, _ = patch(session_client, workspace, project, parent, {**MOVED, "offer_sub_items": True})

        assert sorted(offered(response)) == sorted(
            [(str(child.id), "2026-01-07", "2026-01-12"), (str(grandchild.id), "2026-01-08", "2026-01-10")]
        )

        response, _ = patch(session_client, workspace, project, parent, {**MOVED, "move_sub_items": True})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(grandchild) == (date(2026, 1, 8), date(2026, 1, 10))
        assert dates(finished) == (date(2026, 1, 2), date(2026, 1, 3))

    def test_moved_earlier_they_follow_unless_that_breaks_what_they_depend_on(self, session_client, workspace, project):
        parent = item(project, "parent", date(2026, 1, 11), date(2026, 1, 20))
        free = item(project, "free", date(2026, 1, 13), date(2026, 1, 15), parent=parent)
        held = item(project, "held", date(2026, 1, 13), date(2026, 1, 15), parent=parent)
        relate(item(project, "before", date(2026, 1, 1), date(2026, 1, 11)), held)

        response, _ = patch(
            session_client,
            workspace,
            project,
            parent,
            {"start_date": "2026-01-06", "finish_date": "2026-01-15", "offer_sub_items": True},
        )

        assert offered(response) == [(str(free.id), "2026-01-08", "2026-01-10")]

    def test_sub_items_take_their_own_dependents_along(
        self, session_client, workspace, project, family, django_capture_on_commit_callbacks
    ):
        parent, child = family
        after_child = item(project, "after child", date(2026, 1, 9), date(2026, 1, 12))
        relate(child, after_child)

        asked, _ = patch(session_client, workspace, project, parent, {**MOVED, "offer_sub_items": True})
        assert asked.json()["shifts"] == []
        assert offered(asked, "shifts_with_sub_items") == [(str(after_child.id), "2026-01-13", "2026-01-16")]

        # ticked, but the dependents are not confirmed: offered again
        again, _ = patch(session_client, workspace, project, parent, {**MOVED, "move_sub_items": True})
        assert value(again, "error_code") == "relation_reschedule_available"
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

        response, activity = patch(
            session_client,
            workspace,
            project,
            parent,
            {**MOVED, "move_sub_items": True, "shift_dependents": True},
            on_commit=django_capture_on_commit_callbacks,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 7), date(2026, 1, 12))
        assert dates(after_child) == (date(2026, 1, 13), date(2026, 1, 16))
        # down the chain the history names the work item the person changed
        assert {call.kwargs["shifted_after"] for call in activity.call_args_list} == {str(parent.id)}

    def test_with_the_offer_switched_off_nothing_follows(self, session_client, workspace, project, family):
        parent, child = family
        Project.objects.filter(pk=project.pk).update(is_reschedule_offer_enabled=False)

        asked, _ = patch(session_client, workspace, project, parent, {**MOVED, "offer_sub_items": True})
        assert asked.status_code == status.HTTP_204_NO_CONTENT

        response, _ = patch(
            session_client,
            workspace,
            project,
            parent,
            {"start_date": "2026-01-07", "finish_date": "2026-01-16", "move_sub_items": True},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(parent) == (date(2026, 1, 7), date(2026, 1, 16))
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))


@pytest.mark.contract
@pytest.mark.django_db
class TestSubItemsThePersonMayNotChange:
    def test_stay_where_they_are(self, workspace, project, family):
        parent, child = family
        Project.objects.filter(pk=project.pk).update(is_assignee_edit_rule_enabled=True)
        member = User.objects.create(email="follow-member@example.com", username="follow-member")
        other = User.objects.create(email="follow-other@example.com", username="follow-other")
        for user in (member, other):
            WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
            ProjectMember.objects.create(project=project, member=user, role=15, is_active=True)
        IssueAssignee.objects.create(issue=parent, assignee=member, project=project, workspace=workspace)
        theirs = item(project, "theirs", date(2026, 1, 3), date(2026, 1, 8), parent=parent)
        IssueAssignee.objects.create(issue=theirs, assignee=other, project=project, workspace=workspace)
        client = APIClient()
        client.force_authenticate(user=member)

        response, _ = patch(client, workspace, project, parent, {**MOVED, "offer_sub_items": True})

        # the unassigned sub-item is open to every member, the one assigned to somebody else is not
        assert offered(response) == [(str(child.id), "2026-01-07", "2026-01-12")]

        response, _ = patch(client, workspace, project, parent, {**MOVED, "move_sub_items": True})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 7), date(2026, 1, 12))
        assert dates(theirs) == (date(2026, 1, 3), date(2026, 1, 8))


@pytest.mark.contract
@pytest.mark.django_db
class TestTimelineDrag:
    def test_dragging_a_parent_offers_its_sub_items(self, session_client, workspace, project, family):
        parent, child = family
        updates = [{"id": str(parent.id), **MOVED}]

        asked = drag(session_client, workspace, project, {"updates": updates, "offer_sub_items": True})

        assert asked.status_code == status.HTTP_400_BAD_REQUEST
        assert offered(asked) == [(str(child.id), "2026-01-07", "2026-01-12")]

        response = drag(
            session_client,
            workspace,
            project,
            {"updates": updates, "shift_dependents": True, "move_sub_items": True},
        )

        assert response.status_code == status.HTTP_200_OK
        assert dates(parent) == (date(2026, 1, 5), date(2026, 1, 14))
        assert dates(child) == (date(2026, 1, 7), date(2026, 1, 12))

    def test_dragging_a_sub_item_past_its_parents_successor_offers_to_shift_it(
        self, session_client, workspace, project, family
    ):
        parent, child = family
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(parent, successor)
        updates = [{"id": str(child.id), "start_date": "2026-01-10", "finish_date": "2026-01-15"}]

        response = drag(session_client, workspace, project, {"updates": updates})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert offered(response, "shifts") == [(str(successor.id), "2026-01-16", "2026-01-25")]


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApi:
    def url(self, workspace, project, issue):
        return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

    def test_sub_items_stay_unless_the_client_asks(self, api_key_client, workspace, project, family):
        parent, child = family

        with mock.patch("plane.api.views.issue.issue_activity"), mock.patch(ACTIVITY):
            response = api_key_client.patch(self.url(workspace, project, parent), MOVED, format="json")

        assert response.status_code == status.HTTP_200_OK, response.content
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 8))

        with mock.patch("plane.api.views.issue.issue_activity"), mock.patch(ACTIVITY):
            response = api_key_client.patch(
                self.url(workspace, project, parent),
                {"start_date": "2026-01-07", "finish_date": "2026-01-16", "move_sub_items": True},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK, response.content
        assert dates(child) == (date(2026, 1, 5), date(2026, 1, 10))


@pytest.mark.contract
@pytest.mark.django_db
class TestEffectiveSpan:
    """As the predecessor a parent counts with the dates of its sub-items where they reach past its own."""

    @pytest.fixture
    def overrun(self, project):
        """A sub-item that already ends after its parent's successor starts, saved before D8c."""
        parent = item(project, "parent", date(2026, 1, 1), date(2026, 1, 10))
        child = item(project, "child", date(2026, 1, 3), date(2026, 1, 14), parent=parent)
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(parent, successor)
        return parent, child, successor

    def test_a_new_relation_counts_the_sub_items(self, session_client, workspace, project, family):
        parent, _ = family
        Issue.objects.filter(pk=family[1].pk).update(finish_date=date(2026, 1, 14))
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))

        with mock.patch("plane.app.views.issue.relation.issue_activity"):
            response = session_client.post(
                issue_url(workspace, project, parent) + "issue-relation/",
                {"relation_type": "blocking", "issues": [str(successor.id)]},
                format="json",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert value(response, "error_code") == "relation_date_conflict"

    def test_the_successor_cannot_start_before_the_sub_items_end(self, session_client, workspace, project, overrun):
        parent, _, successor = overrun

        response, _ = patch(session_client, workspace, project, successor, {"start_date": "2026-01-12"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert value(response, "error_code") == "relation_date_conflict"
        assert value(response, "related_ref") == f"FOL-{parent.sequence_id}"

    def test_shortening_an_overrun_that_was_there_is_not_refused(self, session_client, workspace, project, overrun):
        _, child, _ = overrun

        response, _ = patch(session_client, workspace, project, child, {"finish_date": "2026-01-12"})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 12))

    def test_lengthening_it_offers_to_shift_the_successor(self, session_client, workspace, project, overrun):
        _, child, successor = overrun

        response, _ = patch(session_client, workspace, project, child, {"finish_date": "2026-01-16"})

        assert value(response, "error_code") == "relation_reschedule_available"
        assert offered(response, "shifts") == [(str(successor.id), "2026-01-17", "2026-01-26")]

    def test_with_the_offer_switched_off_the_overrun_is_refused(self, session_client, workspace, project, overrun):
        parent, child, successor = overrun
        Project.objects.filter(pk=project.pk).update(is_reschedule_offer_enabled=False)

        response, _ = patch(session_client, workspace, project, child, {"finish_date": "2026-01-16"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert value(response, "error_code") == "relation_date_conflict"
        # the refusal names the parent, whose span the sub-item widens
        assert value(response, "issue_ref") == f"FOL-{parent.sequence_id}"
        assert value(response, "related_ref") == f"FOL-{successor.sequence_id}"
        assert dates(child) == (date(2026, 1, 3), date(2026, 1, 14))
