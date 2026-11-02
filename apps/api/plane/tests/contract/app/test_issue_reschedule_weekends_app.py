# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Relations count working days: 'must start after', the lag and the shifted dependents skip the weekend days."""

from datetime import date
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember

ACTIVITY = "plane.utils.issue_reschedule.issue_activity.delay"

# 2 November 2026 is a Monday
MON, THU, FRI, SAT = date(2026, 11, 2), date(2026, 11, 5), date(2026, 11, 6), date(2026, 11, 7)
NEXT_MON, NEXT_TUE, NEXT_WED = date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11)
WED = date(2026, 11, 4)
EARLIER_FRI = date(2026, 10, 30)


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Work", identifier="WRK", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def item(project, name, start=None, finish=None):
    issue = Issue.objects.create(
        name=name, workspace=project.workspace, project=project, start_date=start, finish_date=finish
    )
    return issue


def block(project, predecessor, successor, lag=0):
    """``successor`` is blocked by ``predecessor``."""
    return IssueRelation.objects.create(
        issue=successor,
        related_issue=predecessor,
        relation_type="blocked_by",
        lag_days=lag,
        project=project,
        workspace=project.workspace,
    )


def patch(client, workspace, project, issue, data):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY),
    ):
        return client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/", data, format="json"
        )


def dates(issue):
    issue.refresh_from_db()
    return issue.start_date, issue.finish_date


@pytest.mark.contract
@pytest.mark.django_db
class TestTheDependentKeepsItsWorkingDays:
    def test_monday_to_wednesday_moved_three_days_ahead_lasts_thursday_to_monday(
        self, session_client, workspace, project
    ):
        predecessor = item(project, "predecessor", date(2026, 10, 26), EARLIER_FRI)
        successor = item(project, "successor", MON, WED)  # three working days
        block(project, predecessor, successor)

        # the predecessor now finishes on Wednesday, so the successor may start on Thursday
        offered = patch(session_client, workspace, project, predecessor, {"finish_date": str(WED)})

        assert offered.status_code == status.HTTP_400_BAD_REQUEST
        shift = offered.json()["shifts"][0]
        # Thursday, Friday and then Monday: the weekend does not count, so the item still lasts three working days
        assert (shift["new_start_date"], shift["new_finish_date"]) == (str(THU), str(NEXT_MON))

    def test_confirmed_the_dates_move_and_the_duration_stays(
        self, session_client, workspace, project, django_capture_on_commit_callbacks
    ):
        predecessor = item(project, "predecessor", date(2026, 10, 26), EARLIER_FRI)
        successor = item(project, "successor", MON, WED)
        Issue.objects.filter(pk=successor.pk).update(duration=3)
        block(project, predecessor, successor)

        with django_capture_on_commit_callbacks(execute=True):
            response = patch(
                session_client, workspace, project, predecessor, {"finish_date": str(WED), "shift_dependents": True}
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        assert dates(successor) == (THU, NEXT_MON)
        successor.refresh_from_db()
        assert successor.duration == 3

    def test_a_predecessor_finishing_on_friday_lets_the_next_item_start_on_monday_not_saturday(
        self, session_client, workspace, project
    ):
        predecessor = item(project, "predecessor", date(2026, 10, 26), EARLIER_FRI)
        successor = item(project, "successor", MON, WED)
        block(project, predecessor, successor)

        offered = patch(session_client, workspace, project, predecessor, {"finish_date": str(FRI)})

        shift = offered.json()["shifts"][0]
        assert (shift["new_start_date"], shift["new_finish_date"]) == (str(NEXT_MON), str(NEXT_WED))

    def test_a_dependent_with_only_a_start_date_moves_just_that_date(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", date(2026, 10, 26), EARLIER_FRI)
        successor = item(project, "successor", MON, None)
        block(project, predecessor, successor)

        offered = patch(session_client, workspace, project, predecessor, {"finish_date": str(FRI)})

        shift = offered.json()["shifts"][0]
        assert (shift["new_start_date"], shift["new_finish_date"]) == (str(NEXT_MON), None)


@pytest.mark.contract
@pytest.mark.django_db
class TestTheRuleItself:
    def test_a_start_on_the_weekend_after_a_friday_finish_is_fine(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", date(2026, 10, 26), FRI)
        successor = item(project, "successor", NEXT_MON, NEXT_WED)
        block(project, predecessor, successor)

        # Saturday stands for Monday: it was allowed when every day counted and it still is
        response = patch(session_client, workspace, project, successor, {"start_date": str(SAT)})

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content

    def test_starting_on_the_day_the_predecessor_finishes_is_refused(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", date(2026, 10, 26), FRI)
        successor = item(project, "successor", NEXT_MON, NEXT_WED)
        block(project, predecessor, successor)

        response = patch(session_client, workspace, project, successor, {"start_date": str(FRI)})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == ["relation_date_conflict"]

    def test_a_lag_counts_working_days(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", date(2026, 10, 26), FRI)
        successor = item(project, "successor", NEXT_WED, date(2026, 11, 12))
        block(project, predecessor, successor, lag=2)

        # two free working days after Friday are Monday and Tuesday: Tuesday is too early, Wednesday is not
        too_early = patch(session_client, workspace, project, successor, {"start_date": str(NEXT_TUE)})
        on_time = patch(session_client, workspace, project, successor, {"start_date": str(NEXT_WED)})

        assert too_early.status_code == status.HTTP_400_BAD_REQUEST
        assert on_time.status_code == status.HTTP_204_NO_CONTENT, on_time.content

    def test_a_project_without_a_weekend_counts_every_day(self, session_client, workspace, project):
        Project.objects.filter(pk=project.pk).update(weekend_days=[])
        predecessor = item(project, "predecessor", date(2026, 10, 26), FRI)
        successor = item(project, "successor", NEXT_MON, NEXT_WED)
        block(project, predecessor, successor)

        # Saturday is a working day here, so it is the first day after Friday
        assert patch(session_client, workspace, project, successor, {"start_date": str(SAT)}).status_code == 204
        assert patch(session_client, workspace, project, successor, {"start_date": str(FRI)}).status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
class TestAcrossProjects:
    def test_the_dependent_is_shifted_by_its_own_projects_weekend(
        self, session_client, workspace, project, create_user
    ):
        other = Project.objects.create(
            name="Seven days", identifier="SVN", workspace=workspace, created_by=create_user, weekend_days=[]
        )
        ProjectMember.objects.create(project=other, member=create_user, role=20, is_active=True)
        predecessor = item(project, "predecessor", date(2026, 10, 26), EARLIER_FRI)
        successor = item(other, "successor", MON, WED)  # three days in a project that works every day
        block(project, predecessor, successor)

        offered = patch(session_client, workspace, project, predecessor, {"finish_date": str(WED)})

        shift = offered.json()["shifts"][0]
        # Thursday to Saturday: the other project has no weekend, so nothing is skipped there
        assert (shift["new_start_date"], shift["new_finish_date"]) == (str(THU), str(SAT))
