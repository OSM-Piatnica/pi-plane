# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The work item API counts working days with the project's weekend days, and a change of those days follows."""

import importlib
from datetime import date
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, Project, ProjectMember, State
from plane.utils.work_item_duration_sync import recompute_project_work_item_durations

# 2 November 2026 is a Monday
MON, WED, FRI, NEXT_MON, NEXT_TUE = (
    date(2026, 11, 2),
    date(2026, 11, 4),
    date(2026, 11, 6),
    date(2026, 11, 9),
    date(2026, 11, 10),
)

ACTIVITY = "plane.bgtasks.issue_activities_task.issue_activity.delay"


@pytest.fixture(autouse=True)
def _no_activity(db):
    with mock.patch(ACTIVITY):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Dur", identifier="DUR", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    State.objects.create(
        name="Todo", project=project, workspace=workspace, group="unstarted", default=True, created_by=create_user
    )
    return project


def issues_url(workspace, project):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"


def create(client, workspace, project, **data):
    response = client.post(issues_url(workspace, project), {"name": "Item", **data}, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return Issue.objects.get(pk=response.json()["id"])


@pytest.mark.contract
@pytest.mark.django_db
class TestApi:
    def test_a_duration_from_dates_skips_the_weekend(self, session_client, workspace, project):
        item = create(session_client, workspace, project, start_date=str(FRI), finish_date=str(NEXT_TUE))

        assert item.duration == 3  # Fri, Mon, Tue

    def test_dates_from_a_duration_skip_the_weekend(self, session_client, workspace, project):
        item = create(session_client, workspace, project, start_date=str(FRI), duration=3)

        assert item.finish_date == NEXT_TUE

    def test_changing_a_date_recounts_the_working_days(self, session_client, workspace, project):
        item = create(session_client, workspace, project, start_date=str(MON), finish_date=str(WED))
        assert item.duration == 3

        response = session_client.patch(
            f"{issues_url(workspace, project)}{item.id}/", {"finish_date": str(NEXT_MON)}, format="json"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.content
        item.refresh_from_db()
        assert item.duration == 6  # Mon - next Mon, Saturday and Sunday left out

    def test_a_project_with_other_weekend_days_counts_them(self, session_client, workspace, project):
        Project.objects.filter(pk=project.pk).update(weekend_days=[5, 6])

        item = create(session_client, workspace, project, start_date=str(MON), finish_date=str(NEXT_MON))

        assert item.duration == 6  # Mon-Thu, then Sunday and the next Monday; Friday and Saturday are off

    def test_a_project_without_a_weekend_counts_calendar_days(self, session_client, workspace, project):
        Project.objects.filter(pk=project.pk).update(weekend_days=[])

        item = create(session_client, workspace, project, start_date=str(FRI), finish_date=str(NEXT_TUE))

        assert item.duration == 5

    def test_the_public_api_uses_the_same_days(self, api_key_client, workspace, project):
        response = api_key_client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/",
            {"name": "Public", "start_date": str(FRI), "finish_date": str(NEXT_TUE)},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.content
        assert Issue.objects.get(pk=response.json()["id"]).duration == 3

    def test_a_timeline_drag_recounts_the_duration(self, session_client, workspace, project):
        item = create(session_client, workspace, project, start_date=str(MON), finish_date=str(WED))

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-dates/",
            {"updates": [{"id": str(item.id), "start_date": str(FRI), "finish_date": str(NEXT_TUE)}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.content
        item.refresh_from_db()
        assert (item.start_date, item.finish_date) == (FRI, NEXT_TUE)


@pytest.mark.contract
@pytest.mark.django_db
class TestWeekendChange:
    def test_the_durations_follow_a_change_of_weekend_days(self, workspace, project, create_user):
        item = Issue.objects.create(
            name="Item", project=project, workspace=workspace, start_date=MON, finish_date=NEXT_MON, duration=6
        )
        no_dates = Issue.objects.create(name="Plain", project=project, workspace=workspace, duration=4)
        Project.objects.filter(pk=project.pk).update(weekend_days=[])

        changed = recompute_project_work_item_durations(project.pk)

        item.refresh_from_db()
        no_dates.refresh_from_db()
        assert changed == 1 and item.duration == 8 and no_dates.duration == 4

    def test_saving_other_weekend_days_schedules_the_recount_after_commit(
        self, workspace, project, django_capture_on_commit_callbacks
    ):
        with mock.patch("plane.bgtasks.project_duration_task.recompute_project_durations.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                project = Project.objects.get(pk=project.pk)
                project.weekend_days = [5, 6]
                project.save()

        delay.assert_called_once_with(str(project.pk))

    def test_saving_the_same_days_or_another_field_schedules_nothing(
        self, workspace, project, django_capture_on_commit_callbacks
    ):
        with mock.patch("plane.bgtasks.project_duration_task.recompute_project_durations.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                project = Project.objects.get(pk=project.pk)
                project.weekend_days = [6, 0]
                project.name = "Renamed"
                project.save()

        delay.assert_not_called()

    def test_the_settings_endpoint_changes_the_durations(
        self, session_client, workspace, project, create_user, django_capture_on_commit_callbacks
    ):
        item = Issue.objects.create(
            name="Item", project=project, workspace=workspace, start_date=MON, finish_date=NEXT_MON, duration=6
        )

        with mock.patch("plane.bgtasks.project_duration_task.recompute_project_durations.delay") as delay:
            with django_capture_on_commit_callbacks(execute=True):
                response = session_client.patch(
                    f"/api/workspaces/{workspace.slug}/projects/{project.id}/", {"weekend_days": [3]}, format="json"
                )

        assert response.status_code == status.HTTP_200_OK, response.content
        delay.assert_called_once()
        recompute_project_work_item_durations(project.pk)
        item.refresh_from_db()
        assert item.duration == 7  # only Wednesday off


@pytest.mark.unit
def test_the_worker_knows_the_recount_task():
    """A task nobody imports is refused by the worker as unregistered, so the durations would never follow."""
    from django.conf import settings

    from plane.bgtasks.project_duration_task import recompute_project_durations

    assert recompute_project_durations.__module__ in settings.CELERY_IMPORTS


@pytest.mark.contract
@pytest.mark.django_db
class TestMigration:
    def test_stored_durations_are_recounted_with_each_projects_days(self, workspace, project, create_user):
        # Migration 0149 predates finish_date: the end of a schedule was then the target date, and it still reads that
        migration = importlib.import_module("plane.db.migrations.0149_work_item_duration_working_days")
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=workspace, created_by=create_user, weekend_days=[]
        )
        weekdays = Issue.objects.create(
            name="A", project=project, workspace=workspace, start_date=MON, target_date=NEXT_MON, duration=8
        )
        calendar = Issue.objects.create(
            name="B", project=other, workspace=workspace, start_date=MON, target_date=NEXT_MON, duration=8
        )
        backwards = Issue.objects.create(
            name="C", project=project, workspace=workspace, start_date=NEXT_MON, target_date=MON, duration=2
        )
        undated = Issue.objects.create(name="D", project=project, workspace=workspace, duration=5)

        # A model in a migration's state has only a base manager, none of the custom ones the live model declares
        class HistoricalModel:
            def __init__(self, model):
                self._base_manager = model._base_manager

        class HistoricalApps:
            @staticmethod
            def get_model(app_label, model_name):
                return HistoricalModel({"Project": Project, "Issue": Issue}[model_name])

        migration.count_working_days_only(HistoricalApps, None)

        for item in (weekdays, calendar, backwards, undated):
            item.refresh_from_db()
        assert weekdays.duration == 6
        assert calendar.duration == 8
        assert backwards.duration == 2
        assert undated.duration == 5
