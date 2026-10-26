# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Several relation types between the same two work items, no loops, and the types beyond blocks/relates/duplicates."""

from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueRelation, Project, ProjectMember

PAIRS = [("implemented_by", "implements"), ("caused_by", "causes"), ("cloned_by", "clones"), ("tested_by", "tests")]


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
        name="Rel",
        identifier="REL",
        workspace=workspace,
        created_by=create_user,
        is_relation_schedule_enabled=True,
        is_relation_traceability_enabled=True,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def items(project):
    return [Issue.objects.create(name=name, project=project, workspace=project.workspace) for name in "abc"]


def url(workspace, project, issue, suffix="issue-relation/"):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/{suffix}"


def relate(client, workspace, project, issue, relation_type, *others):
    return client.post(
        url(workspace, project, issue),
        {"relation_type": relation_type, "issues": [str(other.id) for other in others]},
        format="json",
    )


def listed(client, workspace, project, issue):
    data = client.get(url(workspace, project, issue)).json()
    return {name: sorted(row["id"] for row in rows) for name, rows in data.items()}


@pytest.mark.contract
@pytest.mark.django_db
class TestSeveralTypesPerPair:
    def test_two_work_items_can_be_related_in_two_ways(self, session_client, workspace, project, items):
        a, b, _ = items

        assert relate(session_client, workspace, project, a, "relates_to", b).status_code == status.HTTP_201_CREATED
        assert relate(session_client, workspace, project, a, "blocked_by", b).status_code == status.HTTP_201_CREATED

        assert IssueRelation.objects.filter(issue=a, related_issue=b).count() == 2
        from_a = listed(session_client, workspace, project, a)
        assert from_a["relates_to"] == [str(b.id)] and from_a["blocked_by"] == [str(b.id)]
        from_b = listed(session_client, workspace, project, b)
        assert from_b["relates_to"] == [str(a.id)] and from_b["blocking"] == [str(a.id)]

    def test_the_same_type_twice_is_stored_once(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "blocked_by", b)
        relate(session_client, workspace, project, a, "blocked_by", b)
        assert IssueRelation.objects.filter(issue=a, related_issue=b, relation_type="blocked_by").count() == 1

    def test_a_symmetric_relation_is_not_stored_again_from_the_other_side(
        self, session_client, workspace, project, items
    ):
        a, b, _ = items
        relate(session_client, workspace, project, a, "relates_to", b)
        relate(session_client, workspace, project, b, "relates_to", a)

        assert IssueRelation.objects.filter(relation_type="relates_to").count() == 1
        assert listed(session_client, workspace, project, a)["relates_to"] == [str(b.id)]
        assert listed(session_client, workspace, project, b)["relates_to"] == [str(a.id)]

    def test_removing_one_type_leaves_the_others(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "relates_to", b)
        relate(session_client, workspace, project, a, "blocked_by", b)

        response = session_client.post(
            url(workspace, project, a, "remove-relation/"),
            {"relation_type": "blocked_by", "related_issue": str(b.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert list(IssueRelation.objects.values_list("relation_type", flat=True)) == ["relates_to"]

    def test_removing_from_the_other_side_uses_the_reverse_name(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "blocked_by", b)

        response = session_client.post(
            url(workspace, project, b, "remove-relation/"),
            {"relation_type": "blocking", "related_issue": str(a.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not IssueRelation.objects.exists()

    def test_removing_without_a_type_is_ambiguous_with_two_relations(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "relates_to", b)
        relate(session_client, workspace, project, a, "blocked_by", b)

        response = session_client.post(
            url(workspace, project, a, "remove-relation/"), {"related_issue": str(b.id)}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert IssueRelation.objects.count() == 2

    def test_removing_a_type_that_is_not_there_is_not_found(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "relates_to", b)

        response = session_client.post(
            url(workspace, project, a, "remove-relation/"),
            {"relation_type": "blocked_by", "related_issue": str(b.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert IssueRelation.objects.count() == 1


@pytest.mark.contract
@pytest.mark.django_db
class TestNoLoops:
    def test_a_work_item_cannot_be_related_to_itself(self, session_client, workspace, project, items):
        a, _, _ = items
        response = relate(session_client, workspace, project, a, "relates_to", a)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == "relation_self"
        assert not IssueRelation.objects.exists()

    def test_two_work_items_cannot_block_each_other(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "blocked_by", b)

        response = relate(session_client, workspace, project, b, "blocked_by", a)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == "relation_cycle"
        assert IssueRelation.objects.count() == 1

    def test_a_longer_chain_cannot_be_closed(self, session_client, workspace, project, items):
        a, b, c = items
        relate(session_client, workspace, project, a, "blocked_by", b)
        relate(session_client, workspace, project, b, "blocked_by", c)

        response = relate(session_client, workspace, project, c, "blocked_by", a)

        assert response.json()["error_code"] == "relation_cycle"

    def test_the_reverse_name_closes_the_same_loop(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "blocked_by", b)

        # "a blocking b" is "b blocked by a"
        response = relate(session_client, workspace, project, a, "blocking", b)

        assert response.json()["error_code"] == "relation_cycle"

    def test_a_chain_in_one_direction_is_fine(self, session_client, workspace, project, items):
        a, b, c = items
        assert relate(session_client, workspace, project, a, "blocked_by", b).status_code == 201
        assert relate(session_client, workspace, project, b, "blocked_by", c).status_code == 201
        assert relate(session_client, workspace, project, a, "blocked_by", c).status_code == 201

    def test_different_types_do_not_make_a_loop(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "blocked_by", b)
        assert relate(session_client, workspace, project, b, "caused_by", a).status_code == status.HTTP_201_CREATED

    def test_symmetric_types_have_no_direction_to_loop_on(self, session_client, workspace, project, items):
        a, b, _ = items
        relate(session_client, workspace, project, a, "duplicate", b)
        assert relate(session_client, workspace, project, b, "duplicate", a).status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestNewTypes:
    @pytest.mark.parametrize("forward, reverse", PAIRS)
    def test_the_two_sides_see_each_others_name(self, session_client, workspace, project, items, forward, reverse):
        a, b, _ = items

        assert relate(session_client, workspace, project, a, forward, b).status_code == status.HTTP_201_CREATED

        row = IssueRelation.objects.get()
        assert (row.issue_id, row.related_issue_id, row.relation_type) == (a.id, b.id, forward)
        assert listed(session_client, workspace, project, a)[forward] == [str(b.id)]
        assert listed(session_client, workspace, project, b)[reverse] == [str(a.id)]

    @pytest.mark.parametrize("forward, reverse", PAIRS)
    def test_the_reverse_name_stores_the_row_the_other_way_round(
        self, session_client, workspace, project, items, forward, reverse
    ):
        a, b, _ = items

        assert relate(session_client, workspace, project, a, reverse, b).status_code == status.HTTP_201_CREATED

        row = IssueRelation.objects.get()
        assert (row.issue_id, row.related_issue_id, row.relation_type) == (b.id, a.id, forward)

    def test_an_unknown_type_is_refused(self, session_client, workspace, project, items):
        a, b, _ = items
        assert relate(session_client, workspace, project, a, "invented", b).status_code == status.HTTP_400_BAD_REQUEST

    def test_the_list_names_every_type(self, session_client, workspace, project, items):
        a, _, _ = items
        names = set(listed(session_client, workspace, project, a))
        assert {
            "implements",
            "implemented_by",
            "causes",
            "caused_by",
            "clones",
            "cloned_by",
            "tests",
            "tested_by",
        } <= names


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicApi:
    def v1(self, workspace, project, issue):
        return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/relations/"

    def test_new_types_and_several_types_per_pair(self, api_key_client, create_user, workspace, project, items):
        a, b, _ = items
        for relation_type in ("relates_to", "caused_by"):
            response = api_key_client.post(
                self.v1(workspace, project, a),
                {"relation_type": relation_type, "issues": [str(b.id)]},
                format="json",
            )
            assert response.status_code == status.HTTP_201_CREATED, response.data

        listed_a = api_key_client.get(self.v1(workspace, project, a)).json()
        assert [row["issue_id"] for row in listed_a["caused_by"]] == [str(b.id)]
        assert [row["issue_id"] for row in listed_a["relates_to"]] == [str(b.id)]
        listed_b = api_key_client.get(self.v1(workspace, project, b)).json()
        assert [row["issue_id"] for row in listed_b["causes"]] == [str(a.id)]

    def test_loops_and_self_relations_are_refused(self, api_key_client, create_user, workspace, project, items):
        a, b, _ = items
        api_key_client.post(
            self.v1(workspace, project, a), {"relation_type": "blocked_by", "issues": [str(b.id)]}, format="json"
        )

        loop = api_key_client.post(
            self.v1(workspace, project, b), {"relation_type": "blocked_by", "issues": [str(a.id)]}, format="json"
        )
        itself = api_key_client.post(
            self.v1(workspace, project, a), {"relation_type": "relates_to", "issues": [str(a.id)]}, format="json"
        )

        assert loop.status_code == status.HTTP_400_BAD_REQUEST and loop.json()["error_code"] == "relation_cycle"
        assert itself.status_code == status.HTTP_400_BAD_REQUEST and itself.json()["error_code"] == "relation_self"
