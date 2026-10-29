# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests: which images a shared project serves to anyone with its link.

``GET /api/public/assets/v2/anchor/<anchor>/<asset>/`` is open to everyone. It serves the images of work item
descriptions the public lists contain and of EXTERNAL comments; the images of Internal comments, of drafts and
archived work items, and uploads that belong to no comment yet are not public.
"""

from datetime import date
from unittest import mock
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import DeployBoard, FileAsset, Issue, IssueComment, Project, State, User

ASSET_URL = "/api/public/assets/v2/anchor/{anchor}/{pk}/"
SIGNED = "https://storage.test/signed"


@pytest.fixture(autouse=True)
def _storage():
    with mock.patch("plane.space.views.asset.get_storage") as storage:
        storage.return_value.generate_presigned_url.return_value = SIGNED
        yield


@pytest.fixture
def shared(db, workspace, create_user):
    project = Project.objects.create(name="Shared", identifier="SHR", workspace=workspace, created_by=create_user)
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)
    board = DeployBoard.objects.create(
        workspace=workspace, project=project, entity_name="project", entity_identifier=project.id
    )
    return {"workspace": workspace, "project": project, "state": state, "board": board, "owner": create_user}


def make_issue(shared, **fields):
    return Issue.objects.create(
        name="Issue", workspace=shared["workspace"], project=shared["project"], state=shared["state"], **fields
    )


def make_asset(shared, entity_type, uploader=None, **bind):
    asset = FileAsset(
        attributes={"name": "image.png", "type": "image/png", "size": 10},
        asset=f"{shared['workspace'].id}/{uuid4().hex}-image.png",
        size=10,
        workspace=shared["workspace"],
        project_id=shared["project"].id,
        entity_type=entity_type,
        is_uploaded=True,
        **bind,
    )
    asset.save(created_by_id=(uploader or shared["owner"]).id)
    return asset


def comment(shared, issue, access):
    return IssueComment.objects.create(
        issue=issue,
        project=shared["project"],
        workspace=shared["workspace"],
        comment_html="<p>c</p>",
        access=access,
        actor=shared["owner"],
    )


def get(shared, asset, client=None):
    return (client or APIClient()).get(ASSET_URL.format(anchor=shared["board"].anchor, pk=asset.id))


@pytest.mark.contract
@pytest.mark.django_db
class TestSpaceAssetVisibility:
    def test_description_image_of_a_listed_work_item_is_served(self, shared):
        asset = make_asset(shared, FileAsset.EntityTypeContext.ISSUE_DESCRIPTION, issue=make_issue(shared))
        response = get(shared, asset)
        assert response.status_code == status.HTTP_302_FOUND
        assert response["Location"] == SIGNED

    @pytest.mark.parametrize("fields", [{"is_draft": True}, {"archived_at": date(2026, 1, 1)}])
    def test_description_image_of_a_draft_or_archived_work_item_is_not(self, shared, fields):
        asset = make_asset(shared, FileAsset.EntityTypeContext.ISSUE_DESCRIPTION, issue=make_issue(shared, **fields))
        assert get(shared, asset).status_code == status.HTTP_404_NOT_FOUND

    def test_image_of_an_external_comment_is_served(self, shared):
        issue = make_issue(shared)
        asset = make_asset(
            shared, FileAsset.EntityTypeContext.COMMENT_DESCRIPTION, comment=comment(shared, issue, "EXTERNAL")
        )
        assert get(shared, asset).status_code == status.HTTP_302_FOUND

    def test_image_of_an_internal_comment_is_not(self, shared):
        issue = make_issue(shared)
        asset = make_asset(
            shared, FileAsset.EntityTypeContext.COMMENT_DESCRIPTION, comment=comment(shared, issue, "INTERNAL")
        )
        assert get(shared, asset).status_code == status.HTTP_404_NOT_FOUND

    def test_upload_without_a_comment_is_for_its_uploader_only(self, shared):
        asset = make_asset(shared, FileAsset.EntityTypeContext.COMMENT_DESCRIPTION)
        assert get(shared, asset).status_code == status.HTTP_404_NOT_FOUND
        stranger = User.objects.create(email=f"s-{uuid4().hex[:6]}@plane.so", username=f"s_{uuid4().hex[:6]}")
        other = APIClient()
        other.force_authenticate(user=stranger)
        assert get(shared, asset, other).status_code == status.HTTP_404_NOT_FOUND
        uploader = APIClient()
        uploader.force_authenticate(user=shared["owner"])
        assert get(shared, asset, uploader).status_code == status.HTTP_302_FOUND

    def test_asset_of_another_project_is_not_served(self, shared):
        other = Project.objects.create(
            name="Other", identifier="OTH", workspace=shared["workspace"], created_by=shared["owner"]
        )
        asset = FileAsset(
            attributes={"name": "i.png", "type": "image/png", "size": 1},
            asset=f"{shared['workspace'].id}/{uuid4().hex}-i.png",
            size=1,
            workspace=shared["workspace"],
            project_id=other.id,
            entity_type=FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
            is_uploaded=True,
        )
        asset.save(created_by_id=shared["owner"].id)
        assert get(shared, asset).status_code == status.HTTP_404_NOT_FOUND
