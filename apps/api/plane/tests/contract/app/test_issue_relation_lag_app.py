# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Lag on a relation: set on creation, changed by posting again, listed, and honoured when dates change."""

from datetime import date
from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember


@pytest.fixture(autouse=True)
def _no_activity(db):
    with (
        mock.patch("plane.app.views.issue.relation.issue_activity"),
        mock.patch("plane.app.views.issue.relation.base_host", return_value="http://testserver"),
        mock.patch("plane.api.views.issue.issue_activity"),
        mock.patch("plane.api.views.issue.base_host", return_value="http://testserver"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Lag",
        identifier="LAG",
        workspace=workspace,
        created_by=create_user,
        is_relation_schedule_enabled=True,
        is_relation_traceability_enabled=True,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


def item(project, name, start=None, finish=None):
    return Issue.objects.create(
        name=name, project=project, workspace=project.workspace, start_date=start, target_date=finish
    )


def url(workspace, project, issue, suffix="issue-relation/"):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/{suffix}"


def relate(client, workspace, project, issue, relation_type, other, **extra):
    return client.post(
        url(workspace, project, issue),
        {"relation_type": relation_type, "issues": [str(other.id)], **extra},
        format="json",
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestLagOnRelations:
    def test_a_relation_is_created_with_its_lag(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")

        response = relate(session_client, workspace, project, a, "blocked_by", b, lag_days=3)

        assert response.status_code == status.HTTP_201_CREATED
        assert IssueRelation.objects.get().lag_days == 3

    def test_no_lag_is_zero(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        relate(session_client, workspace, project, a, "blocked_by", b)
        assert IssueRelation.objects.get().lag_days == 0

    def test_the_list_shows_the_lag_from_both_sides(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        relate(session_client, workspace, project, a, "blocked_by", b, lag_days=-2)

        from_a = session_client.get(url(workspace, project, a)).json()
        from_b = session_client.get(url(workspace, project, b)).json()

        assert [(row["id"], row["lag_days"]) for row in from_a["blocked_by"]] == [(str(b.id), -2)]
        assert [(row["id"], row["lag_days"]) for row in from_b["blocking"]] == [(str(a.id), -2)]

    def test_posting_an_existing_relation_again_changes_its_lag(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        relate(session_client, workspace, project, a, "blocked_by", b, lag_days=1)

        relate(session_client, workspace, project, a, "blocked_by", b, lag_days=4)
        # from the other side, by the reverse name
        relate(session_client, workspace, project, b, "blocking", a, lag_days=5)

        assert IssueRelation.objects.count() == 1
        assert IssueRelation.objects.get().lag_days == 5

    def test_posting_it_again_without_a_lag_keeps_the_lag(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        relate(session_client, workspace, project, a, "blocked_by", b, lag_days=2)
        relate(session_client, workspace, project, a, "blocked_by", b)
        assert IssueRelation.objects.get().lag_days == 2

    @pytest.mark.parametrize("bad", [1.5, "x", 99999, True])
    def test_a_lag_must_be_a_whole_number_in_range(self, session_client, workspace, project, bad):
        a, b = item(project, "a"), item(project, "b")
        response = relate(session_client, workspace, project, a, "blocked_by", b, lag_days=bad)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not IssueRelation.objects.exists()

    def test_only_timeline_relations_have_a_lag(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        response = relate(session_client, workspace, project, a, "relates_to", b, lag_days=2)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_the_lag_is_part_of_the_date_rule(self, session_client, workspace, project):
        blocker = item(project, "blocker", date(2026, 1, 1), date(2026, 1, 10))
        # starts the day after the blocker finishes: fine without a lag, not with two days of it
        blocked = item(project, "blocked", date(2026, 1, 11), date(2026, 1, 20))

        ok = relate(session_client, workspace, project, blocked, "blocked_by", blocker)
        refused = relate(session_client, workspace, project, blocked, "blocked_by", blocker, lag_days=2)

        assert ok.status_code == status.HTTP_201_CREATED
        assert refused.status_code == status.HTTP_400_BAD_REQUEST
        assert refused.json()["error_code"] == "relation_date_conflict"
        assert refused.json()["lag_days"] == 2
        assert IssueRelation.objects.get().lag_days == 0

    def test_changing_dates_respects_the_lag(self, session_client, workspace, project):
        blocker = item(project, "blocker", date(2026, 1, 1), date(2026, 1, 10))
        blocked = item(project, "blocked", date(2026, 1, 13), date(2026, 1, 20))
        relate(session_client, workspace, project, blocked, "blocked_by", blocker, lag_days=2)
        patch_url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{blocked.id}/"

        too_early = session_client.patch(patch_url, {"start_date": "2026-01-12"}, format="json")
        on_time = session_client.patch(patch_url, {"start_date": "2026-01-14"}, format="json")

        assert too_early.status_code == status.HTTP_400_BAD_REQUEST
        assert on_time.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.contract
@pytest.mark.django_db
class TestStartToFinishRelation:
    def test_is_created_and_seen_from_both_sides(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")

        response = relate(session_client, workspace, project, a, "start_before_finish", b, lag_days=1)

        assert response.status_code == status.HTTP_201_CREATED
        row = IssueRelation.objects.get()
        assert (row.issue_id, row.related_issue_id, row.relation_type, row.lag_days) == (
            a.id,
            b.id,
            "start_before_finish",
            1,
        )
        assert [r["id"] for r in session_client.get(url(workspace, project, b)).json()["finish_after_start"]] == [
            str(a.id)
        ]

    def test_the_related_item_cannot_finish_before_this_one_starts(self, session_client, workspace, project):
        a = item(project, "a", date(2026, 1, 10), date(2026, 1, 20))
        b = item(project, "b", date(2026, 1, 1), date(2026, 1, 9))

        refused = relate(session_client, workspace, project, a, "start_before_finish", b)

        assert refused.status_code == status.HTTP_400_BAD_REQUEST
        assert refused.json()["error_code"] == "relation_date_conflict"
        assert refused.json()["relation_type"] == "start_before_finish"

    def test_a_loop_is_refused_like_the_other_directed_types(self, session_client, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        relate(session_client, workspace, project, a, "start_before_finish", b)
        response = relate(session_client, workspace, project, b, "start_before_finish", a)
        assert response.json()["error_code"] == "relation_cycle"


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApiLag:
    def v1(self, workspace, project, issue):
        return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/relations/"

    def test_create_with_a_lag_and_list_it(self, api_key_client, create_user, workspace, project):
        a, b = item(project, "a"), item(project, "b")

        created = api_key_client.post(
            self.v1(workspace, project, a),
            {"relation_type": "start_before_finish", "issues": [str(b.id)], "lag_days": 2},
            format="json",
        )
        listed = api_key_client.get(self.v1(workspace, project, a)).json()

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert [(row["issue_id"], row["lag_days"]) for row in listed["start_before_finish"]] == [(str(b.id), 2)]

    def test_relations_without_dates_are_listed_as_before(self, api_key_client, create_user, workspace, project):
        a, b = item(project, "a"), item(project, "b")
        api_key_client.post(
            self.v1(workspace, project, a), {"relation_type": "relates_to", "issues": [str(b.id)]}, format="json"
        )

        listed = api_key_client.get(self.v1(workspace, project, a)).json()

        assert listed["relates_to"] == [{"project_id": str(project.id), "issue_id": str(b.id)}]
