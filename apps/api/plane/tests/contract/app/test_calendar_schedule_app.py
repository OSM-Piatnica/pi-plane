# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The calendar of the planned work: which work items a window of days loads, and how they are grouped."""

import pytest

from plane.db.models import Issue, Project, ProjectMember, State

ADMIN = 20


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Calendar", identifier="CAL", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


@pytest.fixture
def issues(workspace, project):
    state = State.objects.get(project=project)
    dates = {
        "both-inside": ("2026-03-10", "2026-03-12"),
        "start-only": ("2026-03-05", None),
        "finish-only": (None, "2026-03-20"),
        "spans-window": ("2026-02-20", "2026-04-10"),
        "starts-inside-ends-later": ("2026-03-28", "2026-05-01"),
        "before": ("2026-01-01", "2026-01-05"),
        "after": ("2026-06-01", "2026-06-05"),
        "start-only-outside": ("2026-07-01", None),
        "undated": (None, None),
    }
    for name, (start, finish) in dates.items():
        Issue.objects.create(
            name=name, project=project, workspace=workspace, state=state, start_date=start, finish_date=finish
        )


def _grouped(response):
    assert response.status_code == 200, response.data
    return {group: sorted(row["name"] for row in value["results"]) for group, value in response.data["results"].items()}


def _names(grouped):
    return sorted(name for names in grouped.values() for name in names)


@pytest.mark.contract
@pytest.mark.django_db
class TestScheduleWindow:
    def _get(self, session_client, workspace, project, **params):
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"
        return session_client.get(url, {"per_page": 50, "cursor": "50:0:0", **params})

    def test_the_window_loads_every_work_item_whose_schedule_touches_it(
        self, session_client, workspace, project, issues
    ):
        grouped = _grouped(
            self._get(
                session_client,
                workspace,
                project,
                group_by="schedule_date",
                schedule_window="2026-03-01;2026-03-31",
            )
        )

        assert _names(grouped) == [
            "both-inside",
            "finish-only",
            "spans-window",
            "start-only",
            "starts-inside-ends-later",
        ]

    def test_work_items_are_grouped_by_their_finish_day_or_their_start_day_without_a_finish(
        self, session_client, workspace, project, issues
    ):
        grouped = _grouped(
            self._get(
                session_client,
                workspace,
                project,
                group_by="schedule_date",
                schedule_window="2026-03-01;2026-03-31",
            )
        )

        assert grouped["2026-03-05"] == ["start-only"]
        assert grouped["2026-03-12"] == ["both-inside"]
        assert grouped["2026-03-20"] == ["finish-only"]

    def test_one_day_of_a_group_is_loaded_with_the_window_still_applied(
        self, session_client, workspace, project, issues
    ):
        response = self._get(
            session_client, workspace, project, schedule_date="2026-03-05", schedule_window="2026-03-01;2026-03-31"
        )
        assert response.status_code == 200, response.data
        assert [row["name"] for row in response.data["results"]] == ["start-only"]

    def test_a_malformed_window_is_ignored(self, session_client, workspace, project, issues):
        response = self._get(session_client, workspace, project, schedule_window="soon;later")

        assert response.status_code == 200, response.data
        assert len(response.data["results"]) == 9
