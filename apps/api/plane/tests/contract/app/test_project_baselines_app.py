# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Baselines of a project: saving the plan, keeping one active, and the variance against it.

June 2027: 1 June is a Tuesday; 4 June is a Friday, 7 and 14 June are Mondays.
"""

from datetime import date
from unittest import mock
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    BaselineItem,
    Cycle,
    CycleIssue,
    Issue,
    Module,
    ModuleIssue,
    Project,
    ProjectBaseline,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

LIST_URL = "/api/workspaces/{slug}/projects/{project_id}/baselines/"
DETAIL_URL = LIST_URL + "{pk}/"
VARIANCE_URL = LIST_URL + "variance/"


@pytest.fixture(autouse=True)
def _no_broker():
    # deleting a baseline soft-deletes its items through a Celery task
    with mock.patch("plane.db.mixins.soft_delete_related_objects"):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Baselines", identifier="BSL", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    # the state a work item saved without one takes
    State.objects.create(name="Todo", project=project, workspace=workspace, group="unstarted", default=True)
    return project


def make_issue(project, author, name, start=None, finish=None, due=None, state=None, **extra):
    issue = Issue(
        name=name,
        project=project,
        workspace=project.workspace,
        state=state,
        start_date=date.fromisoformat(start) if start else None,
        finish_date=date.fromisoformat(finish) if finish else None,
        target_date=date.fromisoformat(due) if due else None,
        **extra,
    )
    issue.save(created_by_id=author.id)
    return issue


def make_user(workspace, project, role, prefix):
    user = User.objects.create(email=f"{prefix}-{uuid4().hex[:6]}@plane.so", username=f"{prefix}_{uuid4().hex[:6]}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    if project is not None:
        ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    return user


def user_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def urls(project, pk=None):
    params = {"slug": project.workspace.slug, "project_id": project.id}
    if pk is not None:
        return DETAIL_URL.format(pk=pk, **params)
    return LIST_URL.format(**params), VARIANCE_URL.format(**params)


def save_baseline(client, project, name="Plan", **data):
    return client.post(urls(project)[0], {"name": name, **data}, format="json")


def variance(client, project, **params):
    return client.get(urls(project)[1], params)


@pytest.fixture
def plan(project, create_user):
    """A: Tuesday 1 to Friday 4 June, due 11 June. B: 7 to 9 June. C has no dates."""
    a = make_issue(project, create_user, "A", "2027-06-01", "2027-06-04", due="2027-06-11")
    b = make_issue(project, create_user, "B", "2027-06-07", "2027-06-09")
    c = make_issue(project, create_user, "C")
    return a, b, c


@pytest.mark.contract
@pytest.mark.django_db
class TestCapture:
    def test_saving_stores_the_dates_and_the_state_group_of_dated_work_items(
        self, session_client, project, create_user, workspace
    ):
        a = make_issue(project, create_user, "A", "2027-06-01", "2027-06-04", due="2027-06-11")
        done = State.objects.create(name="Done", project=project, workspace=workspace, group="completed")
        b = make_issue(project, create_user, "B", "2027-06-07", "2027-06-09", state=done)
        only_due = make_issue(project, create_user, "Due", due="2027-06-18")
        make_issue(project, create_user, "Undated")

        response = save_baseline(session_client, project, "  Plan 1  ", description="approved")
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert (body["name"], body["description"], body["is_active"]) == ("Plan 1", "approved", True)
        assert body["item_count"] == 3
        assert body["created_by"] == str(create_user.id)

        baseline = ProjectBaseline.objects.get(pk=body["id"])
        assert (baseline.project_id, baseline.workspace_id) == (project.id, workspace.id)
        items = {item.issue_id: item for item in BaselineItem.objects.filter(baseline=baseline)}
        assert set(items) == {a.id, b.id, only_due.id}
        assert (items[a.id].start_date, items[a.id].finish_date, items[a.id].target_date) == (
            date(2027, 6, 1),
            date(2027, 6, 4),
            date(2027, 6, 11),
        )
        assert items[a.id].state_group == "unstarted"
        assert items[a.id].completed_at is None
        assert items[b.id].state_group == "completed"
        assert items[b.id].completed_at is not None
        assert (items[only_due.id].start_date, items[only_due.id].target_date) == (None, date(2027, 6, 18))
        assert items[a.id].project_id == project.id
        assert items[a.id].workspace_id == workspace.id
        assert items[a.id].created_by_id == create_user.id

    def test_deleted_archived_draft_and_other_projects_work_items_are_not_captured(
        self, session_client, project, create_user
    ):
        kept = make_issue(project, create_user, "Kept", "2027-06-01", "2027-06-04")
        deleted = make_issue(project, create_user, "Deleted", "2027-06-01", "2027-06-04")
        Issue.objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())
        archived = make_issue(project, create_user, "Archived", "2027-06-01", "2027-06-04")
        Issue.objects.filter(pk=archived.pk).update(archived_at=timezone.now())
        make_issue(project, create_user, "Draft", "2027-06-01", "2027-06-04", is_draft=True)
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=project.workspace, created_by=create_user
        )
        make_issue(other, create_user, "Elsewhere", "2027-06-01", "2027-06-04")

        body = save_baseline(session_client, project).json()
        assert body["item_count"] == 1
        assert list(BaselineItem.objects.filter(baseline_id=body["id"]).values_list("issue_id", flat=True)) == [kept.id]

    def test_the_number_of_queries_does_not_grow_with_the_work_items(self, session_client, project, create_user):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        make_issue(project, create_user, "First", "2027-06-01", "2027-06-04")
        with CaptureQueriesContext(connection) as few:
            assert save_baseline(session_client, project, "One").status_code == status.HTTP_201_CREATED
        for index in range(12):
            make_issue(project, create_user, f"More {index}", "2027-06-01", "2027-06-04")
        with CaptureQueriesContext(connection) as many:
            response = save_baseline(session_client, project, "Two")
        assert response.json()["item_count"] == 13
        assert len(many) == len(few)

    def test_a_name_is_required_and_bounded(self, session_client, project, plan):
        assert save_baseline(session_client, project, "   ").status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.post(urls(project)[0], {}, format="json").status_code == status.HTTP_400_BAD_REQUEST
        assert save_baseline(session_client, project, "x" * 256).status_code == status.HTTP_400_BAD_REQUEST
        assert save_baseline(session_client, project, 5).status_code == status.HTTP_400_BAD_REQUEST
        assert (
            save_baseline(session_client, project, "ok", description="d" * 2001).status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert ProjectBaseline.objects.count() == 0

    def test_a_project_keeps_a_limited_number_of_baselines(self, session_client, project, plan):
        with mock.patch("plane.utils.baselines.MAX_BASELINES_PER_PROJECT", 2):
            assert save_baseline(session_client, project, "One").status_code == status.HTTP_201_CREATED
            second = save_baseline(session_client, project, "Two")
            assert second.status_code == status.HTTP_201_CREATED
            refused = save_baseline(session_client, project, "Three")
            assert refused.status_code == status.HTTP_400_BAD_REQUEST
            assert refused.json()["code"] == "baseline_limit_reached"
            # nothing changed: the second one is still the active one
            assert ProjectBaseline.objects.filter(project=project).count() == 2
            assert ProjectBaseline.objects.get(is_active=True).name == "Two"
            # a deleted baseline frees a place
            assert session_client.delete(urls(project, second.json()["id"])).status_code == 204
            assert save_baseline(session_client, project, "Three").status_code == status.HTTP_201_CREATED

    def test_the_limit_is_stated(self, session_client, project):
        body = session_client.get(urls(project)[0]).json()
        assert body == {"baselines": [], "max_baselines": 20}


@pytest.mark.contract
@pytest.mark.django_db
class TestOneActiveBaseline:
    def test_a_new_baseline_becomes_the_active_one_and_older_ones_are_kept(self, session_client, project, plan):
        first = save_baseline(session_client, project, "First").json()
        second = save_baseline(session_client, project, "Second").json()
        body = session_client.get(urls(project)[0]).json()
        # newest first
        assert [(row["name"], row["is_active"]) for row in body["baselines"]] == [("Second", True), ("First", False)]
        assert body["baselines"][0]["id"] == second["id"]
        assert BaselineItem.objects.filter(baseline_id=first["id"]).count() == 2

    def test_any_baseline_can_be_made_active(self, session_client, project, plan):
        first = save_baseline(session_client, project, "First").json()
        second = save_baseline(session_client, project, "Second").json()
        response = session_client.patch(urls(project, first["id"]), {"is_active": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is True
        assert list(ProjectBaseline.objects.filter(is_active=True).values_list("id", flat=True)) == [
            ProjectBaseline.objects.get(pk=first["id"]).id
        ]
        # and none at all
        response = session_client.patch(urls(project, first["id"]), {"is_active": False}, format="json")
        assert response.json()["is_active"] is False
        assert not ProjectBaseline.objects.filter(is_active=True).exists()
        assert ProjectBaseline.objects.filter(pk=second["id"]).exists()
        assert (
            session_client.patch(urls(project, first["id"]), {"is_active": "yes"}, format="json").status_code
            == status.HTTP_400_BAD_REQUEST
        )

    def test_the_database_refuses_two_active_baselines_of_a_project(self, project, create_user):
        ProjectBaseline.objects.create(project=project, name="One", is_active=True)
        with pytest.raises(IntegrityError), transaction.atomic():
            ProjectBaseline.objects.create(project=project, name="Two", is_active=True)
        # a deleted active baseline does not stand in the way
        ProjectBaseline.objects.filter(project=project).update(deleted_at=timezone.now())
        ProjectBaseline.objects.create(project=project, name="Three", is_active=True)

    def test_baselines_of_projects_do_not_touch_each_other(self, session_client, project, plan, create_user):
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=project.workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=other, member=create_user, workspace=project.workspace, role=20)
        mine = save_baseline(session_client, project, "Mine").json()
        theirs = save_baseline(session_client, other, "Theirs").json()
        assert ProjectBaseline.objects.filter(is_active=True).count() == 2
        # a baseline is only reachable through its own project
        assert session_client.get(urls(other, mine["id"])).status_code == status.HTTP_404_NOT_FOUND
        assert session_client.delete(urls(project, theirs["id"])).status_code == status.HTTP_404_NOT_FOUND
        assert variance(session_client, other, baseline=mine["id"]).status_code == status.HTTP_404_NOT_FOUND

    def test_rename_describe_and_delete(self, session_client, project, plan):
        baseline = save_baseline(session_client, project, "First").json()
        response = session_client.patch(
            urls(project, baseline["id"]), {"name": " Approved plan ", "description": "v2"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert (response.json()["name"], response.json()["description"]) == ("Approved plan", "v2")
        # renaming does not change which one is active
        assert response.json()["is_active"] is True
        assert (
            session_client.patch(urls(project, baseline["id"]), {"name": ""}, format="json").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert ProjectBaseline.objects.get(pk=baseline["id"]).name == "Approved plan"

        assert session_client.delete(urls(project, baseline["id"])).status_code == status.HTTP_204_NO_CONTENT
        assert session_client.get(urls(project)[0]).json()["baselines"] == []
        assert session_client.get(urls(project, baseline["id"])).status_code == status.HTTP_404_NOT_FOUND
        # deleting the active baseline leaves the project without one
        body = variance(session_client, project).json()
        assert body["baseline"] is None
        assert body["items"] == {}

    def test_retrieve_answers_the_items(self, session_client, project, plan):
        a, b, _ = plan
        baseline = save_baseline(session_client, project).json()
        body = session_client.get(urls(project, baseline["id"])).json()
        assert body["id"] == baseline["id"]
        items = {item["issue"]: item for item in body["items"]}
        assert set(items) == {str(a.id), str(b.id)}
        assert items[str(a.id)]["start_date"] == "2027-06-01"
        assert items[str(a.id)]["finish_date"] == "2027-06-04"
        assert items[str(a.id)]["target_date"] == "2027-06-11"
        assert items[str(a.id)]["state_group"] == "unstarted"
        assert items[str(a.id)]["completed_at"] is None


@pytest.mark.contract
@pytest.mark.django_db
class TestVariance:
    def test_variance_counts_working_days_across_a_weekend(self, session_client, project, plan):
        a, b, _ = plan
        baseline = save_baseline(session_client, project).json()
        # A finishes on Wednesday 9 June instead of Friday 4 June: Monday, Tuesday, Wednesday
        Issue.objects.filter(pk=a.pk).update(start_date=date(2027, 6, 3), finish_date=date(2027, 6, 9))
        # B starts and finishes a week earlier, Monday to Monday is five working days
        Issue.objects.filter(pk=b.pk).update(start_date=date(2027, 5, 31), finish_date=date(2027, 6, 2))

        response = variance(session_client, project)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["baseline"]["id"] == baseline["id"]
        assert body["weekend_days"] == [0, 6]
        assert body["items"][str(a.id)] == {
            "in_baseline": True,
            "baseline_start_date": "2027-06-01",
            "start_date": "2027-06-03",
            "start_date_variance": 2,
            "baseline_finish_date": "2027-06-04",
            "finish_date": "2027-06-09",
            "finish_date_variance": 3,
            "baseline_target_date": "2027-06-11",
            "target_date": "2027-06-11",
        }
        assert body["items"][str(b.id)]["start_date_variance"] == -5
        assert body["items"][str(b.id)]["finish_date_variance"] == -5
        # the due date is a deadline: it is answered, but it is no part of the variance
        assert "target_date_variance" not in body["items"][str(b.id)]
        # the plan ended on 9 June (B) and still does (A)
        assert body["summary"] == {"baseline_end": "2027-06-09", "current_end": "2027-06-09", "end_variance": 0}

    def test_the_weekend_days_of_the_project_are_used(self, session_client, project, plan):
        a, *_ = plan
        save_baseline(session_client, project)
        Issue.objects.filter(pk=a.pk).update(finish_date=date(2027, 6, 9))
        Project.objects.filter(pk=project.pk).update(weekend_days=[])
        body = variance(session_client, project).json()
        assert body["weekend_days"] == []
        assert body["items"][str(a.id)]["finish_date_variance"] == 5

    def test_work_items_added_after_the_baseline_have_no_baseline_dates(
        self, session_client, project, plan, create_user
    ):
        a, b, c = plan
        save_baseline(session_client, project)
        new = make_issue(project, create_user, "New", "2027-06-14", "2027-06-18")
        make_issue(project, create_user, "New and undated")
        # C had no dates when the baseline was saved, so the baseline does not know it either
        Issue.objects.filter(pk=c.pk).update(start_date=date(2027, 6, 1))
        body = variance(session_client, project).json()
        assert set(body["items"]) == {str(a.id), str(b.id), str(c.id), str(new.id)}
        for work_item in (new, c):
            entry = body["items"][str(work_item.id)]
            assert entry["in_baseline"] is False
            assert entry["baseline_start_date"] is None and entry["baseline_finish_date"] is None
            assert entry["start_date_variance"] is None and entry["finish_date_variance"] is None
        assert body["items"][str(new.id)]["finish_date"] == "2027-06-18"
        # the new work item ends the project seven working days after the plan did
        assert body["summary"] == {"baseline_end": "2027-06-09", "current_end": "2027-06-18", "end_variance": 7}

    def test_work_items_deleted_or_archived_since_are_left_out(self, session_client, project, plan):
        a, b, _ = plan
        baseline = save_baseline(session_client, project).json()
        Issue.objects.filter(pk=b.pk).update(deleted_at=timezone.now())
        body = variance(session_client, project).json()
        assert set(body["items"]) == {str(a.id)}
        assert body["summary"]["baseline_end"] == "2027-06-04"
        # nor does the baseline itself list it any more
        detail = session_client.get(urls(project, baseline["id"])).json()
        assert [item["issue"] for item in detail["items"]] == [str(a.id)]
        Issue.objects.filter(pk=a.pk).update(archived_at=timezone.now())
        assert variance(session_client, project).json()["items"] == {}

    def test_a_work_item_that_lost_its_dates_keeps_its_baseline_dates(self, session_client, project, plan):
        a, *_ = plan
        save_baseline(session_client, project)
        Issue.objects.filter(pk=a.pk).update(start_date=None, finish_date=None, target_date=None)
        entry = variance(session_client, project).json()["items"][str(a.id)]
        assert entry["in_baseline"] is True
        assert (entry["baseline_finish_date"], entry["finish_date"], entry["finish_date_variance"]) == (
            "2027-06-04",
            None,
            None,
        )

    def test_another_baseline_can_be_chosen(self, session_client, project, plan):
        a, *_ = plan
        first = save_baseline(session_client, project, "First").json()
        Issue.objects.filter(pk=a.pk).update(finish_date=date(2027, 6, 7))
        second = save_baseline(session_client, project, "Second").json()
        Issue.objects.filter(pk=a.pk).update(finish_date=date(2027, 6, 8))

        body = variance(session_client, project).json()
        assert body["baseline"]["id"] == second["id"]
        assert body["items"][str(a.id)]["finish_date_variance"] == 1
        body = variance(session_client, project, baseline=first["id"]).json()
        assert (body["baseline"]["id"], body["baseline"]["is_active"]) == (first["id"], False)
        assert body["items"][str(a.id)]["finish_date_variance"] == 2
        assert variance(session_client, project, baseline="nope").status_code == status.HTTP_400_BAD_REQUEST
        assert variance(session_client, project, baseline=str(uuid4())).status_code == status.HTTP_404_NOT_FOUND

    def test_without_a_baseline_there_is_nothing_to_compare(self, session_client, project, plan):
        body = variance(session_client, project).json()
        assert body == {
            "baseline": None,
            "items": {},
            "summary": {"baseline_end": None, "current_end": None, "end_variance": None},
            "weekend_days": [0, 6],
        }

    def test_module_and_cycle_scope(self, session_client, project, plan, create_user, workspace):
        a, b, _ = plan
        save_baseline(session_client, project)
        module = Module.objects.create(name="M", project=project, workspace=workspace)
        cycle = Cycle.objects.create(name="C", project=project, workspace=workspace, owned_by=create_user)
        ModuleIssue.objects.create(module=module, issue=a, project=project, workspace=workspace)
        CycleIssue.objects.create(cycle=cycle, issue=b, project=project, workspace=workspace)
        body = variance(session_client, project, module=str(module.id)).json()
        assert set(body["items"]) == {str(a.id)}
        assert body["summary"]["baseline_end"] == "2027-06-04"
        assert set(variance(session_client, project, cycle=str(cycle.id)).json()["items"]) == {str(b.id)}
        assert variance(session_client, project, module="nope").status_code == status.HTTP_400_BAD_REQUEST

    def test_the_number_of_queries_does_not_grow_with_the_work_items(self, session_client, project, create_user):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        make_issue(project, create_user, "First", "2027-06-01", "2027-06-04")
        save_baseline(session_client, project, "One")
        with CaptureQueriesContext(connection) as few:
            assert len(variance(session_client, project).json()["items"]) == 1
        for index in range(12):
            make_issue(project, create_user, f"More {index}", "2027-06-01", "2027-06-04")
        save_baseline(session_client, project, "Two")
        with CaptureQueriesContext(connection) as many:
            assert len(variance(session_client, project).json()["items"]) == 13
        assert len(many) == len(few)


@pytest.mark.contract
@pytest.mark.django_db
class TestPermissions:
    def test_a_member_can_save_rename_activate_and_delete(self, workspace, project, plan):
        member = user_client(make_user(workspace, project, 15, "m"))
        first = save_baseline(member, project, "First")
        assert first.status_code == status.HTTP_201_CREATED
        second = save_baseline(member, project, "Second").json()
        url = urls(project, first.json()["id"])
        assert member.patch(url, {"name": "Renamed"}, format="json").status_code == status.HTTP_200_OK
        assert member.patch(url, {"is_active": True}, format="json").json()["is_active"] is True
        assert member.delete(urls(project, second["id"])).status_code == status.HTTP_204_NO_CONTENT

    def test_a_guest_reads_but_does_not_change(self, workspace, project, plan, session_client):
        baseline = save_baseline(session_client, project).json()
        guest = user_client(make_user(workspace, project, 5, "g"))
        url = urls(project, baseline["id"])
        assert save_baseline(guest, project, "Mine").status_code == status.HTTP_403_FORBIDDEN
        assert guest.patch(url, {"name": "Renamed"}, format="json").status_code == status.HTTP_403_FORBIDDEN
        assert guest.patch(url, {"is_active": False}, format="json").status_code == status.HTTP_403_FORBIDDEN
        assert guest.delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert ProjectBaseline.objects.get(pk=baseline["id"]).name == "Plan"
        assert guest.get(urls(project)[0]).status_code == status.HTTP_200_OK
        assert guest.get(url).status_code == status.HTTP_200_OK
        assert variance(guest, project).status_code == status.HTTP_200_OK

    def test_a_guest_only_sees_their_own_work_items(self, workspace, project, plan, session_client):
        a, b, _ = plan
        guest_user = make_user(workspace, project, 5, "g")
        mine = make_issue(project, guest_user, "Mine", "2027-06-01", "2027-06-02")
        baseline = save_baseline(session_client, project).json()
        Issue.objects.filter(pk=mine.pk).update(finish_date=date(2027, 6, 3))
        guest = user_client(guest_user)

        body = variance(guest, project).json()
        assert set(body["items"]) == {str(mine.id)}
        assert body["items"][str(mine.id)]["finish_date_variance"] == 1
        # the end is the end of what the guest sees
        assert body["summary"] == {"baseline_end": "2027-06-02", "current_end": "2027-06-03", "end_variance": 1}
        assert body["baseline"]["item_count"] is None
        detail = guest.get(urls(project, baseline["id"])).json()
        assert [item["issue"] for item in detail["items"]] == [str(mine.id)]
        assert detail["item_count"] is None
        assert guest.get(urls(project)[0]).json()["baselines"][0]["item_count"] is None

        # a project that lets guests see everything shows all of it
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        assert set(variance(guest, project).json()["items"]) == {str(a.id), str(b.id), str(mine.id)}
        assert len(guest.get(urls(project, baseline["id"])).json()["items"]) == 3
        assert guest.get(urls(project)[0]).json()["baselines"][0]["item_count"] == 3

    def test_someone_outside_the_project_is_refused(self, workspace, project, plan, session_client):
        baseline = save_baseline(session_client, project).json()
        stranger = user_client(make_user(workspace, None, 15, "s"))
        assert stranger.get(urls(project)[0]).status_code == status.HTTP_403_FORBIDDEN
        assert save_baseline(stranger, project).status_code == status.HTTP_403_FORBIDDEN
        assert stranger.get(urls(project, baseline["id"])).status_code == status.HTTP_403_FORBIDDEN
        assert stranger.delete(urls(project, baseline["id"])).status_code == status.HTTP_403_FORBIDDEN
        assert variance(stranger, project).status_code == status.HTTP_403_FORBIDDEN
