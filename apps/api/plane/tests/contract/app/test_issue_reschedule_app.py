# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A date change that comes too early for what depends on it is offered with the dependents shifted along."""

from datetime import date
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember, State

ACTIVITY = "plane.utils.issue_reschedule.issue_activity.delay"


@pytest.fixture
def project(db, workspace, create_user):
    # These tests count calendar days, so the project has no weekend; the working-day rules have their own tests
    project = Project.objects.create(
        name="Shift", identifier="SHF", workspace=workspace, created_by=create_user, weekend_days=[]
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, workspace, project):
    return {
        "todo": State.objects.create(
            name="Todo", project=project, workspace=workspace, group="unstarted", default=True
        ),
        "done": State.objects.create(name="Done", project=project, workspace=workspace, group="completed"),
    }


def item(project, name, start=None, finish=None, state=None):
    return Issue.objects.create(
        name=name, workspace=project.workspace, project=project, start_date=start, finish_date=finish, state=state
    )


def relate(project, predecessor, successor, relation_type="blocked_by", lag=0):
    """``successor`` is blocked by / starts after / ... ``predecessor`` (the row is stored on the successor)."""
    stored = {"blocked_by": "blocked_by", "start_before": "start_before", "finish_before": "finish_before"}
    if relation_type == "blocked_by":
        issue, related = successor, predecessor
    else:
        issue, related = predecessor, successor
    return IssueRelation.objects.create(
        issue=issue,
        related_issue=related,
        relation_type=stored.get(relation_type, relation_type),
        lag_days=lag,
        project=project,
        workspace=project.workspace,
    )


def patch_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"


def patch(client, workspace, project, issue, data):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY) as activity,
    ):
        response = client.patch(patch_url(workspace, project, issue), data, format="json")
    return response, activity


def code(response):
    """The error code of a refusal: a serializer wraps every value of its error in a list, a view does not."""
    value = response.json()["error_code"]
    return value[0] if isinstance(value, list) else value


def dates(issue):
    issue.refresh_from_db()
    return issue.start_date, issue.finish_date


@pytest.mark.contract
@pytest.mark.django_db
class TestOfferToShiftDependents:
    def test_the_change_is_offered_with_what_would_move(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", date(2026, 1, 1), date(2026, 1, 10))
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, predecessor, successor)

        response, _ = patch(session_client, workspace, project, predecessor, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = response.json()
        assert body["error_code"] == "relation_reschedule_available"
        assert body["original_error_code"] == "relation_date_conflict"
        assert [(s["id"], s["new_start_date"], s["new_finish_date"]) for s in body["shifts"]] == [
            (str(successor.id), "2026-01-15", "2026-01-24")
        ]
        # nothing moved yet
        assert dates(predecessor) == (date(2026, 1, 1), date(2026, 1, 10))
        assert dates(successor) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_confirmed_the_change_and_the_shift_are_applied_together(
        self, session_client, workspace, project, django_capture_on_commit_callbacks
    ):
        predecessor = item(project, "predecessor", date(2026, 1, 1), date(2026, 1, 10))
        successor = item(project, "successor", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, predecessor, successor)

        with (
            mock.patch("plane.app.views.issue.base.issue_activity"),
            mock.patch("plane.app.views.issue.base.model_activity"),
            mock.patch(ACTIVITY) as activity,
            django_capture_on_commit_callbacks(execute=True),
        ):
            response = session_client.patch(
                patch_url(workspace, project, predecessor),
                {"finish_date": "2026-01-14", "shift_dependents": True},
                format="json",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(predecessor) == (date(2026, 1, 1), date(2026, 1, 14))
        assert dates(successor) == (date(2026, 1, 15), date(2026, 1, 24))
        recorded = sorted(call.kwargs["requested_data"] for call in activity.call_args_list)
        assert recorded == ['{"finish_date": "2026-01-24"}', '{"start_date": "2026-01-15"}']

    def test_the_shift_follows_the_chain(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 15))
        c = item(project, "c", date(2026, 1, 16), date(2026, 1, 20))
        relate(project, a, b)
        relate(project, b, c)

        response, _ = patch(
            session_client, workspace, project, a, {"finish_date": "2026-01-12", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(b) == (date(2026, 1, 13), date(2026, 1, 17))
        assert dates(c) == (date(2026, 1, 18), date(2026, 1, 22))

    def test_only_what_has_to_move_moves(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        roomy = item(project, "roomy", date(2026, 2, 1), date(2026, 2, 10))
        tight = item(project, "tight", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, roomy)
        relate(project, a, tight)

        response, _ = patch(
            session_client, workspace, project, a, {"finish_date": "2026-01-14", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(roomy) == (date(2026, 2, 1), date(2026, 2, 10))
        assert dates(tight) == (date(2026, 1, 15), date(2026, 1, 24))

    def test_a_lag_is_kept(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 13), date(2026, 1, 20))
        relate(project, a, b, lag=2)

        response, _ = patch(
            session_client, workspace, project, a, {"finish_date": "2026-01-12", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(b) == (date(2026, 1, 15), date(2026, 1, 22))

    @pytest.mark.parametrize(
        "relation_type, change, expected",
        [
            # start-to-start: the successor starts on or after the predecessor
            ("start_before", {"start_date": "2026-01-05"}, (date(2026, 1, 5), date(2026, 1, 14))),
            # finish-to-finish: the successor finishes on or after the predecessor
            ("finish_before", {"finish_date": "2026-01-16"}, (date(2026, 1, 7), date(2026, 1, 16))),
        ],
    )
    def test_start_to_start_and_finish_to_finish(
        self, session_client, workspace, project, relation_type, change, expected
    ):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 3), date(2026, 1, 12))
        relate(project, a, b, relation_type=relation_type)

        response, _ = patch(session_client, workspace, project, a, {**change, "shift_dependents": True})

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        assert dates(b) == expected

    def test_start_to_finish(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 5))
        b = item(project, "b", date(2026, 1, 3), date(2026, 1, 12))
        relate(project, a, b, relation_type="start_before_finish")

        # a starts on Jan 20: b may not finish before that
        response, _ = patch(
            session_client,
            workspace,
            project,
            a,
            {"start_date": "2026-01-20", "finish_date": "2026-01-25", "shift_dependents": True},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        assert dates(b) == (date(2026, 1, 11), date(2026, 1, 20))

    def test_not_offered_for_a_completed_dependent(self, session_client, workspace, project, states):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        done = item(project, "done", date(2026, 1, 11), date(2026, 1, 20), state=states["done"])
        relate(project, a, done)

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"

    def test_not_offered_when_the_work_item_itself_is_too_early(self, session_client, workspace, project):
        blocker = item(project, "blocker", date(2026, 1, 1), date(2026, 1, 10))
        blocked = item(project, "blocked", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, blocker, blocked)

        # moving the blocked item earlier cannot be fixed by moving what depends on it
        response, _ = patch(session_client, workspace, project, blocked, {"start_date": "2026-01-05"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"

    def test_not_offered_for_a_dependent_the_person_may_not_edit(self, session_client, workspace, create_user, project):
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=workspace, created_by=create_user, weekend_days=[]
        )
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        elsewhere = item(other, "elsewhere", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, elsewhere)

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"

    def test_a_dependent_in_another_project_is_shifted_when_the_person_may_edit_it(
        self, session_client, workspace, create_user, project
    ):
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=workspace, created_by=create_user, weekend_days=[]
        )
        ProjectMember.objects.create(project=other, member=create_user, role=15, is_active=True)
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        elsewhere = item(other, "elsewhere", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, elsewhere)

        response, _ = patch(
            session_client, workspace, project, a, {"finish_date": "2026-01-14", "shift_dependents": True}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert dates(elsewhere) == (date(2026, 1, 15), date(2026, 1, 24))

    def test_a_change_that_breaks_nothing_needs_no_confirmation(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 2, 1), date(2026, 2, 10))
        relate(project, a, b)

        response, activity = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_204_NO_CONTENT
        activity.assert_not_called()
        assert dates(b) == (date(2026, 2, 1), date(2026, 2, 10))

    def test_a_loop_across_relation_types_is_not_followed_for_ever(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, b)  # b after a (finish to start)
        relate(project, b, a, relation_type="start_before")  # a's start is at least b's start: a cycle across types

        response, _ = patch(session_client, workspace, project, a, {"finish_date": "2026-01-14"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert code(response) == "relation_date_conflict"


@pytest.mark.contract
@pytest.mark.django_db
class TestTimelineDrag:
    def url(self, workspace, project):
        return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-dates/"

    def test_offered_and_then_applied_with_the_batch(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, b)
        update = {"id": str(a.id), "start_date": "2026-01-05", "finish_date": "2026-01-14"}

        with mock.patch("plane.app.views.issue.base.issue_activity"), mock.patch(ACTIVITY):
            offered = session_client.post(self.url(workspace, project), {"updates": [update]}, format="json")
            assert offered.status_code == status.HTTP_400_BAD_REQUEST
            assert offered.json()["error_code"] == "relation_reschedule_available"
            assert dates(a) == (date(2026, 1, 1), date(2026, 1, 10))

            applied = session_client.post(
                self.url(workspace, project), {"updates": [update], "shift_dependents": True}, format="json"
            )

        assert applied.status_code == status.HTTP_200_OK
        assert dates(a) == (date(2026, 1, 5), date(2026, 1, 14))
        assert dates(b) == (date(2026, 1, 15), date(2026, 1, 24))


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApi:
    def url(self, workspace, project, issue):
        return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

    def test_offered_and_then_applied(self, api_key_client, create_user, workspace, project):
        a = item(project, "a", date(2026, 1, 1), date(2026, 1, 10))
        b = item(project, "b", date(2026, 1, 11), date(2026, 1, 20))
        relate(project, a, b)

        with mock.patch(ACTIVITY):
            offered = api_key_client.patch(
                self.url(workspace, project, a), {"finish_date": "2026-01-14"}, format="json"
            )
            applied = api_key_client.patch(
                self.url(workspace, project, a), {"finish_date": "2026-01-14", "shift_dependents": True}, format="json"
            )

        assert offered.status_code == status.HTTP_400_BAD_REQUEST
        assert offered.json()["error_code"] == "relation_reschedule_available"
        assert applied.status_code == status.HTTP_200_OK, applied.data
        assert dates(b) == (date(2026, 1, 15), date(2026, 1, 24))
