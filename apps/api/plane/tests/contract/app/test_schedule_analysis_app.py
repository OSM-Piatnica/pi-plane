# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The schedule analysis of a project (critical path, float, "needed by"), for the timeline.

June 2027: 1 June is a Tuesday, the Mondays are 7, 14, 21 and 28 June.
"""

from datetime import date
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Cycle,
    CycleIssue,
    Issue,
    IssueRelation,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

URL = "/api/workspaces/{slug}/projects/{project_id}/schedule-analysis/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Schedule", identifier="SCH", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


def make_issue(project, author, name, start=None, finish=None, due=None, state=None):
    issue = Issue(
        name=name,
        project=project,
        workspace=project.workspace,
        state=state,
        start_date=date.fromisoformat(start) if start else None,
        finish_date=date.fromisoformat(finish) if finish else None,
        target_date=date.fromisoformat(due) if due else None,
    )
    issue.save(created_by_id=author.id)
    return issue


def relate(issue, related, relation_type="blocked_by", lag=0):
    return IssueRelation.objects.create(
        issue=issue,
        related_issue=related,
        relation_type=relation_type,
        lag_days=lag,
        project=issue.project,
        workspace=issue.workspace,
    )


def user_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def get(client, project, **params):
    return client.get(URL.format(slug=project.workspace.slug, project_id=project.id), params)


@pytest.mark.contract
@pytest.mark.django_db
class TestScheduleAnalysis:
    @pytest.fixture
    def network(self, project, create_user):
        """A then B then C (due 25 June) end on 16 June; D runs alone until 18 June and sets the end."""
        a = make_issue(project, create_user, "A", "2027-06-07", "2027-06-09")
        b = make_issue(project, create_user, "B", "2027-06-10", "2027-06-11")
        c = make_issue(project, create_user, "C", "2027-06-14", "2027-06-16", due="2027-06-25")
        d = make_issue(project, create_user, "D", "2027-06-07", "2027-06-18")
        relate(b, a)
        relate(c, b)
        return a, b, c, d

    def test_answers_float_critical_path_and_needed_by(self, session_client, project, network):
        a, b, c, d = network
        response = get(session_client, project)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert (body["project_start"], body["project_end"]) == ("2027-06-07", "2027-06-18")
        assert body["critical_ids"] == [str(d.id)]
        assert body["critical_links"] == []
        assert body["items"][str(a.id)] == {
            "earliest_start": "2027-06-07",
            "earliest_finish": "2027-06-09",
            "latest_start": "2027-06-09",
            "latest_finish": "2027-06-11",
            "total_float": 2,
            "is_critical": False,
            "is_fixed": False,
            # C (3 days) is due on 25 June, so B (2 days) is needed by 22 June and A by 18 June
            "needed_by": "2027-06-18",
        }
        assert body["items"][str(b.id)]["needed_by"] == "2027-06-22"
        assert body["items"][str(c.id)]["needed_by"] is None
        assert {key: item["total_float"] for key, item in body["items"].items()} == {
            str(a.id): 2,
            str(b.id): 2,
            str(c.id): 2,
            str(d.id): 0,
        }
        assert body["cycles"] == []
        assert body["weekend_days"] == [0, 6]
        assert (body["analysed_count"], body["truncated"], body["undated_count"]) == (4, False, 0)
        assert body["max_items"] == 2000

    def test_uses_the_weekend_days_of_the_project(self, session_client, project, network):
        a, *_ = network
        # every day is a working day: the weekend of 12-13 June between B and C becomes two more days of float
        Project.objects.filter(pk=project.pk).update(weekend_days=[])
        body = get(session_client, project).json()
        assert body["weekend_days"] == []
        assert body["items"][str(a.id)]["total_float"] == 4
        assert body["items"][str(a.id)]["latest_finish"] == "2027-06-13"

    def test_lag_and_the_other_relation_types_are_read_from_the_relations(self, session_client, project, create_user):
        a = make_issue(project, create_user, "A", "2027-06-07", "2027-06-08")
        b = make_issue(project, create_user, "B", "2027-06-11", "2027-06-14")
        relate(b, a, lag=2)
        s = make_issue(project, create_user, "S", "2027-06-07", "2027-06-07")
        relate(s, b, "start_before", lag=3)
        body = get(session_client, project).json()
        # two free days between A and B, and B starts at least 3 working days after S (7 + 3 = 10 June, it starts 11)
        assert body["items"][str(a.id)]["total_float"] == 0
        assert body["items"][str(s.id)]["total_float"] == 1
        assert sorted(body["critical_ids"]) == sorted([str(a.id), str(b.id)])

    def test_completed_work_items_are_fixed(self, session_client, project, create_user, workspace):
        # before the state exists: a work item saved without a state takes the first one of the project
        a = make_issue(project, create_user, "A", "2027-06-07", "2027-06-18")
        done = State.objects.create(name="Done", project=project, workspace=workspace, group="completed")
        b = make_issue(project, create_user, "B", "2027-06-07", "2027-06-18", state=done)
        body = get(session_client, project).json()
        assert body["items"][str(b.id)]["is_fixed"] is True
        assert body["items"][str(b.id)]["total_float"] is None
        assert body["critical_ids"] == [str(a.id)]

    def test_undated_archived_and_deleted_work_items(self, session_client, project, network, create_user):
        a, b, c, d = network
        undated = make_issue(project, create_user, "Undated")
        half = make_issue(project, create_user, "Start only", "2027-06-01")
        relate(a, half)
        body = get(session_client, project).json()
        assert (body["undated_count"], body["inverted_count"]) == (2, 0)
        assert body["undated_linked_ids"] == [str(half.id)]
        assert str(undated.id) not in body["items"] and str(half.id) not in body["items"]
        # a finish before the start is left out and counted on its own, and does not count towards the cap
        inverted = make_issue(project, create_user, "Inverted", "2027-06-01", "2027-06-02")
        Issue.objects.filter(pk=inverted.pk).update(finish_date=date(2027, 5, 28))
        relate(inverted, a)
        body = get(session_client, project).json()
        assert (body["undated_count"], body["inverted_count"], body["analysed_count"]) == (2, 1, 4)
        assert sorted(body["undated_linked_ids"]) == sorted([str(half.id), str(inverted.id)])
        assert str(inverted.id) not in body["items"]
        # D set the end; archived, the chain A-B-C does
        Issue.objects.filter(pk=d.pk).update(archived_at=timezone.now())
        body = get(session_client, project).json()
        assert body["project_end"] == "2027-06-16"
        assert sorted(body["critical_ids"]) == sorted([str(a.id), str(b.id), str(c.id)])
        assert sorted((link["source"], link["target"]) for link in body["critical_links"]) == sorted(
            [(str(a.id), str(b.id)), (str(b.id), str(c.id))]
        )
        # a deleted relation no longer counts
        IssueRelation.objects.filter(issue=c, related_issue=b).update(deleted_at=timezone.now())
        body = get(session_client, project).json()
        assert body["critical_ids"] == [str(c.id)]

    def test_a_cycle_is_reported(self, session_client, project, create_user):
        a = make_issue(project, create_user, "A", "2027-06-07", "2027-06-08")
        b = make_issue(project, create_user, "B", "2027-06-07", "2027-06-08")
        relate(a, b)
        relate(b, a)
        body = get(session_client, project).json()
        assert [sorted(cycle) for cycle in body["cycles"]] == [sorted([str(a.id), str(b.id)])]
        assert set(body["items"]) == {str(a.id), str(b.id)}

    def test_module_and_cycle_scope(self, session_client, project, network, create_user, workspace):
        a, b, c, d = network
        module = Module.objects.create(name="M", project=project, workspace=workspace)
        cycle = Cycle.objects.create(name="C", project=project, workspace=workspace, owned_by=create_user)
        for issue in (a, b):
            ModuleIssue.objects.create(module=module, issue=issue, project=project, workspace=workspace)
        CycleIssue.objects.create(cycle=cycle, issue=d, project=project, workspace=workspace)
        body = get(session_client, project, module=str(module.id)).json()
        assert set(body["items"]) == {str(a.id), str(b.id)}
        # within the module the end is B's finish, so A and B are critical
        assert body["project_end"] == "2027-06-11"
        assert sorted(body["critical_ids"]) == sorted([str(a.id), str(b.id)])
        body = get(session_client, project, cycle=str(cycle.id)).json()
        assert set(body["items"]) == {str(d.id)}
        assert get(session_client, project, module="nope").status_code == status.HTTP_400_BAD_REQUEST
        assert get(session_client, project, module=str(uuid4())).json()["items"] == {}

    def test_work_items_of_another_project_do_not_take_part(self, session_client, project, network, create_user):
        a, *_ = network
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=project.workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=other, member=create_user, workspace=project.workspace, role=20)
        late = make_issue(other, create_user, "Late", "2027-06-10", "2027-09-30")
        relate(late, a)
        body = get(session_client, project).json()
        assert str(late.id) not in body["items"]
        assert body["project_end"] == "2027-06-18"
        assert body["items"][str(a.id)]["total_float"] == 2

    def test_more_dated_work_items_than_the_cap(self, session_client, project, network):
        with mock.patch("plane.utils.schedule_scope.analyse_queryset") as analyse:
            from plane.utils.schedule_analysis import analyse_queryset

            analyse.side_effect = lambda queryset, project_id, weekend_days: analyse_queryset(
                queryset, project_id, weekend_days, max_items=2
            )
            body = get(session_client, project).json()
        a, b, c, d = network
        assert (body["truncated"], body["max_items"], body["analysed_count"]) == (True, 2, 2)
        # the first two by start date, then finish date
        assert set(body["items"]) == {str(a.id), str(d.id)}

    def test_a_non_member_is_refused(self, workspace, project, network):
        stranger = User.objects.create(email=f"s-{uuid4().hex[:6]}@plane.so", username=f"s_{uuid4().hex[:6]}")
        WorkspaceMember.objects.create(workspace=workspace, member=stranger, role=15)
        assert get(user_client(stranger), project).status_code == status.HTTP_403_FORBIDDEN

    def test_a_guest_only_gets_the_analysis_of_their_own_work_items(self, workspace, project, network):
        a, b, c, d = network
        guest = User.objects.create(email=f"g-{uuid4().hex[:6]}@plane.so", username=f"g_{uuid4().hex[:6]}")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
        ProjectMember.objects.create(project=project, member=guest, workspace=workspace, role=5)
        mine = make_issue(project, guest, "Mine", "2027-06-07", "2027-06-08")
        relate(a, mine)
        body = get(user_client(guest), project).json()
        assert set(body["items"]) == {str(mine.id)}
        assert body["project_end"] == "2027-06-08"
        assert body["undated_linked_ids"] == []
        # a project that lets guests see everything shows all of it
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        body = get(user_client(guest), project).json()
        assert len(body["items"]) == 5
