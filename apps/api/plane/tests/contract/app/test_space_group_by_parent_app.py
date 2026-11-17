# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Public boards do not group by parent: the app does, and the shared paginator accepts it, but a public request for it
is refused instead of answered with empty groups."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import DeployBoard, Issue, Project, ProjectMember, State

ISSUES_URL = "/api/public/anchor/{anchor}/issues/"


@pytest.fixture
def board(db, workspace, create_user):
    project = Project.objects.create(name="Shared", identifier="SH", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    State.objects.create(
        name="Todo", group="unstarted", color="#ff0000", project=project, workspace=workspace, default=True
    )
    parent = Issue(name="Parent", project=project, workspace=workspace)
    parent.save(created_by_id=create_user.id)
    Issue(name="Child", project=project, workspace=workspace, parent=parent).save(created_by_id=create_user.id)
    deploy_board = DeployBoard.objects.create(
        entity_name="project", entity_identifier=project.id, project=project, workspace=workspace
    )
    return deploy_board.anchor


@pytest.mark.contract
@pytest.mark.django_db
class TestPublicBoardGrouping:
    def get(self, anchor, **params):
        return APIClient().get(ISSUES_URL.format(anchor=anchor), params)

    def test_grouping_by_parent_is_refused(self, board):
        response = self.get(board, group_by="parent_id")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parent_id" in str(response.data["detail"])

    def test_sub_grouping_by_parent_is_refused(self, board):
        response = self.get(board, group_by="state_id", sub_group_by="parent_id")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_the_groupings_a_public_board_offers_still_work(self, board):
        response = self.get(board, group_by="state_id")

        assert response.status_code == status.HTTP_200_OK
