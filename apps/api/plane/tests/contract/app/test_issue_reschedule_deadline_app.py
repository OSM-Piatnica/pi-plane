# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The shift offer warns about every shifted work item whose new finish date passes its due date (D8b)."""

from datetime import date
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember

ACTIVITY = "plane.utils.issue_reschedule.issue_activity.delay"

# 2 November 2026 is a Monday; the project has Saturday and Sunday as weekend days
MON, TUE, WED, THU, FRI = (date(2026, 11, day) for day in range(2, 7))
NEXT_MON, NEXT_FRI = date(2026, 11, 9), date(2026, 11, 13)
EARLIER_MON, EARLIER_FRI = date(2026, 10, 26), date(2026, 10, 30)


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Demo", identifier="DEMO", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def item(project, name, start=None, finish=None, due=None):
    return Issue.objects.create(
        name=name,
        workspace=project.workspace,
        project=project,
        start_date=start,
        finish_date=finish,
        target_date=due,
    )


def block(project, predecessor, successor):
    """``successor`` is blocked by ``predecessor``."""
    return IssueRelation.objects.create(
        issue=successor,
        related_issue=predecessor,
        relation_type="blocked_by",
        project=project,
        workspace=project.workspace,
    )


def offer(client, workspace, project, issue, data):
    with (
        mock.patch("plane.app.views.issue.base.issue_activity"),
        mock.patch("plane.app.views.issue.base.model_activity"),
        mock.patch(ACTIVITY),
    ):
        response = client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/", data, format="json"
        )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
    return {shift["id"]: shift for shift in response.json()["shifts"]}


@pytest.mark.contract
@pytest.mark.django_db
class TestDeadlineWarning:
    def test_a_shifted_item_passing_its_due_date_carries_the_overrun_in_working_days(
        self, session_client, workspace, project
    ):
        predecessor = item(project, "predecessor", EARLIER_MON, EARLIER_FRI)
        successor = item(project, "successor", MON, WED, due=WED)
        block(project, predecessor, successor)

        shifts = offer(session_client, workspace, project, predecessor, {"finish_date": str(WED)})

        shift = shifts[str(successor.id)]
        # moved to Thursday - Monday: Thursday, Friday and Monday are past the Wednesday due date
        assert shift["new_finish_date"] == str(NEXT_MON)
        assert shift["target_date"] == str(WED)
        assert shift["deadline_overrun_days"] == 3
        assert shift["previous_deadline_overrun_days"] is None

    def test_no_warning_without_a_due_date_or_within_it(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", EARLIER_MON, EARLIER_FRI)
        undated = item(project, "no due date", MON, WED)
        roomy = item(project, "due later", MON, WED, due=NEXT_FRI)
        block(project, predecessor, undated)
        block(project, predecessor, roomy)

        shifts = offer(session_client, workspace, project, predecessor, {"finish_date": str(WED)})

        for issue in (undated, roomy):
            assert shifts[str(issue.id)]["deadline_overrun_days"] is None
        assert shifts[str(undated.id)]["target_date"] is None

    def test_an_item_late_already_gets_both_figures(self, session_client, workspace, project):
        predecessor = item(project, "predecessor", EARLIER_MON, EARLIER_FRI)
        late = item(project, "late", MON, WED, due=TUE)
        block(project, predecessor, late)

        shifts = offer(session_client, workspace, project, predecessor, {"finish_date": str(WED)})

        shift = shifts[str(late.id)]
        assert shift["deadline_overrun_days"] == 4
        assert shift["previous_deadline_overrun_days"] == 1

    def test_items_further_down_the_chain_are_warned_about_too(self, session_client, workspace, project):
        a = item(project, "a", EARLIER_MON, EARLIER_FRI)
        b = item(project, "b", MON, TUE)
        c = item(project, "c", WED, THU, due=FRI)
        block(project, a, b)
        block(project, b, c)

        # a now finishes on Wednesday: b moves to Thursday - Friday and c to Monday - Tuesday
        shifts = offer(session_client, workspace, project, a, {"finish_date": str(WED)})

        assert shifts[str(b.id)]["deadline_overrun_days"] is None
        assert shifts[str(c.id)]["new_finish_date"] == "2026-11-10"
        assert shifts[str(c.id)]["deadline_overrun_days"] == 2

    def test_the_due_date_itself_is_never_shifted(
        self, session_client, workspace, project, django_capture_on_commit_callbacks
    ):
        predecessor = item(project, "predecessor", EARLIER_MON, EARLIER_FRI)
        successor = item(project, "successor", MON, WED, due=WED)
        block(project, predecessor, successor)

        with (
            mock.patch("plane.app.views.issue.base.issue_activity"),
            mock.patch("plane.app.views.issue.base.model_activity"),
            mock.patch(ACTIVITY),
            django_capture_on_commit_callbacks(execute=True),
        ):
            response = session_client.patch(
                f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{predecessor.id}/",
                {"finish_date": str(WED), "shift_dependents": True},
                format="json",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        successor.refresh_from_db()
        assert (successor.finish_date, successor.target_date) == (NEXT_MON, WED)
