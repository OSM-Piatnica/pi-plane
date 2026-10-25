# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Comment html written through the public API is sanitized, on create and on update.

``IssueCommentCreateSerializer`` had no ``validate()``, so ``<script>`` and ``onerror`` payloads in
``comment_html`` were stored exactly as sent. The web client parses stored html through its editor and
is not the exposure; every other consumer of the API is.
"""

from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import APIToken, Issue, IssueComment, Project, ProjectMember

PAYLOADS = [
    "<p>hi</p><script>alert(1)</script>",
    '<p>hi</p><img src=x onerror="alert(1)">',
    '<p><a href="javascript:alert(1)">click</a></p>',
    '<p onclick="alert(1)">hi</p>',
]


@pytest.fixture
def commenting(db, workspace, create_user):
    project = Project.objects.create(name="Comments", identifier="CMT", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    issue = Issue(name="Issue", workspace=workspace, project=project)
    issue.save(created_by_id=create_user.id)
    token = APIToken.objects.create(user=create_user, label="Comments", token="comment-sanitization-token")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    base = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/comments/"
    return client, base, issue


def _unsafe(html):
    lowered = html.lower()
    return any(marker in lowered for marker in ("<script", "onerror", "onclick", "javascript:"))


@pytest.mark.contract
@pytest.mark.django_db
class TestCommentHtmlSanitization:
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_create_stores_nothing_executable(self, commenting, payload):
        client, base, _ = commenting

        with mock.patch("plane.api.views.issue.issue_activity"):
            response = client.post(base, {"comment_html": payload}, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        stored = IssueComment.objects.get(pk=response.data["id"]).comment_html
        assert not _unsafe(stored), stored
        assert "hi" in stored or "click" in stored, "the harmless text survives"

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_update_stores_nothing_executable(self, commenting, payload):
        client, base, issue = commenting
        comment = IssueComment.objects.create(
            issue=issue, project=issue.project, workspace=issue.workspace, comment_html="<p>before</p>"
        )

        with mock.patch("plane.api.views.issue.issue_activity"):
            response = client.patch(f"{base}{comment.id}/", {"comment_html": payload}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        comment.refresh_from_db()
        assert not _unsafe(comment.comment_html), comment.comment_html

    def test_ordinary_formatting_is_kept(self, commenting):
        client, base, _ = commenting
        html = '<p>see <strong>this</strong> and <a href="https://example.com/a">that</a></p><ul><li>one</li></ul>'

        with mock.patch("plane.api.views.issue.issue_activity"):
            response = client.post(base, {"comment_html": html}, format="json")

        stored = IssueComment.objects.get(pk=response.data["id"]).comment_html
        assert "<strong>this</strong>" in stored
        assert 'href="https://example.com/a"' in stored
        assert "<li>one</li>" in stored

    def test_html_that_cannot_be_checked_is_refused(self, commenting):
        client, base, _ = commenting

        with mock.patch("plane.api.serializers.issue.validate_html_content", return_value=(False, "bad", None)):
            response = client.post(base, {"comment_html": "<p>x</p>"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not IssueComment.objects.exists()
