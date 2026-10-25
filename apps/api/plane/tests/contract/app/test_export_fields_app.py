# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""ExportIssuesEndpoint accepts the columns to export."""

from unittest.mock import patch

import pytest
from rest_framework import status

from plane.db.models import ExporterHistory


def _url(slug):
    return f"/api/workspaces/{slug}/export-issues/"


@pytest.mark.contract
@pytest.mark.django_db
class TestExportFieldsEndpoint:
    @patch("plane.app.views.exporter.base.issue_export_task")
    def test_the_chosen_columns_reach_the_task_and_the_history(self, task, session_client, workspace):
        response = session_client.post(
            _url(workspace.slug), {"provider": "csv", "project": [], "fields": ["priority", "labels"]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        expected = ["identifier", "name", "priority", "labels"]
        assert task.delay.call_args.kwargs["export_fields"] == expected
        assert ExporterHistory.objects.get().filters == {"fields": expected}

    @patch("plane.app.views.exporter.base.issue_export_task")
    def test_without_fields_everything_is_exported(self, task, session_client, workspace):
        response = session_client.post(_url(workspace.slug), {"provider": "csv", "project": []}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert task.delay.call_args.kwargs["export_fields"] is None
        assert ExporterHistory.objects.get().filters is None

    @patch("plane.app.views.exporter.base.issue_export_task")
    def test_an_empty_choice_still_exports_the_required_columns(self, task, session_client, workspace):
        session_client.post(_url(workspace.slug), {"provider": "csv", "project": [], "fields": []}, format="json")

        assert task.delay.call_args.kwargs["export_fields"] == ["identifier", "name"]

    @patch("plane.app.views.exporter.base.issue_export_task")
    def test_an_unknown_column_is_refused_and_nothing_is_queued(self, task, session_client, workspace):
        response = session_client.post(
            _url(workspace.slug), {"provider": "csv", "project": [], "fields": ["bogus"]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "bogus" in response.data["error"]
        task.delay.assert_not_called()
        assert not ExporterHistory.objects.exists()
