# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""What the work item import records in its history when the file cannot be processed."""

import json
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from plane.db.models import ExporterHistory, Project, ProjectMember

ADMIN = 20
SLUG = "test-workspace"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="History", identifier="HST", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


def _upload(project):
    rows = [{"external_key": "A", "name": "One"}]
    return {
        "project_id": str(project.id),
        "provider": "json",
        "file": SimpleUploadedFile("items.json", json.dumps(rows).encode(), content_type="application/json"),
    }


@pytest.mark.contract
@pytest.mark.django_db
class TestImportHistoryReason:
    def test_an_unexpected_error_is_not_recorded_in_the_history(self, session_client, project):
        secret = 'relation "issues" does not exist at /srv/plane/internal.py'
        with mock.patch(
            "plane.app.views.importer.work_items.import_community_work_items_into_project",
            side_effect=RuntimeError(secret),
        ):
            response = session_client.post(f"/api/workspaces/{SLUG}/import-work-items/", _upload(project))

        assert response.status_code == 400
        assert secret not in json.dumps(response.json())
        history = ExporterHistory.objects.get(type="project_imports")
        assert history.status == "failed"
        assert history.reason == "Could not read the file."
