# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The largest upload, set by the instance administrator in the admin app.

A saved limit applies to new uploads; the environment default (``FILE_SIZE_LIMIT``) applies until one is saved or
when it is cleared; the deployment's ceiling (``FILE_SIZE_LIMIT_MAX``) bounds what can be saved. Lowering the limit
never touches files that are already stored.
"""

from unittest import mock
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from plane.db.models import FileAsset, Issue, Project, ProjectMember, State
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.file_size_limit import MIN_FILE_SIZE_LIMIT, get_file_size_limit, get_file_size_limit_max

KEY = "FILE_SIZE_LIMIT"
CONFIGURATIONS = "/api/instances/configurations/"
INSTANCE = "/api/instances/"
MB = 1024 * 1024


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Test",
        instance_id=uuid4().hex,
        current_version="1.0.0",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def instance_admin(instance, create_user):
    return InstanceAdmin.objects.create(instance=instance, user=create_user, role=20)


@pytest.fixture
def setting(db):
    return InstanceConfiguration.objects.create(key=KEY, value="", category="WORKSPACE_MANAGEMENT")


def save(client, value):
    return client.patch(CONFIGURATIONS, {KEY: value}, format="json")


def reported_limit(client):
    return client.get(INSTANCE).data["config"]["file_size_limit"]


@pytest.mark.contract
@pytest.mark.django_db
class TestSavingTheLimit:
    def test_a_limit_in_range_is_saved_and_reported(self, session_client, instance_admin, setting):
        response = save(session_client, str(20 * MB))
        assert response.status_code == 200, response.data
        setting.refresh_from_db()
        assert setting.value == str(20 * MB)
        assert reported_limit(session_client) == 20 * MB

    def test_the_instance_reports_the_ceiling_too(self, session_client, instance_admin, setting):
        assert session_client.get(INSTANCE).data["config"]["file_size_limit_max"] == get_file_size_limit_max()

    @pytest.mark.parametrize("value", ["abc", "1.5", "-5", "0", str(MIN_FILE_SIZE_LIMIT - 1)])
    def test_a_value_that_is_not_a_sensible_size_is_refused(self, session_client, instance_admin, setting, value):
        response = save(session_client, value)
        assert response.status_code == 400, response.data
        setting.refresh_from_db()
        assert setting.value == ""

    def test_more_than_the_ceiling_is_refused(self, session_client, instance_admin, setting):
        response = save(session_client, str(get_file_size_limit_max() + 1))
        assert response.status_code == 400
        setting.refresh_from_db()
        assert setting.value == ""

    def test_empty_goes_back_to_the_default(self, session_client, instance_admin, setting):
        save(session_client, str(20 * MB))
        assert save(session_client, "").status_code == 200
        assert reported_limit(session_client) == settings.FILE_SIZE_LIMIT


@pytest.mark.unit
@pytest.mark.django_db
class TestReadingTheLimit:
    def test_no_saved_value_means_the_environment_default(self, setting):
        assert get_file_size_limit() == settings.FILE_SIZE_LIMIT

    def test_a_missing_setting_means_the_environment_default(self, db):
        assert get_file_size_limit() == settings.FILE_SIZE_LIMIT

    def test_a_saved_value_wins(self, setting):
        setting.value = str(30 * MB)
        setting.save()
        assert get_file_size_limit() == 30 * MB

    def test_a_saved_value_is_kept_inside_the_allowed_range(self, setting):
        setting.value = str(10 * 1024 * MB)
        setting.save()
        assert get_file_size_limit() == get_file_size_limit_max()
        setting.value = "10"
        setting.save()
        assert get_file_size_limit() == MIN_FILE_SIZE_LIMIT

    def test_garbage_means_the_environment_default(self, setting):
        setting.value = "lots"
        setting.save()
        assert get_file_size_limit() == settings.FILE_SIZE_LIMIT

    @override_settings(SKIP_ENV_VAR=False)
    def test_the_database_is_ignored_when_the_environment_rules(self, setting):
        setting.value = str(30 * MB)
        setting.save()
        assert get_file_size_limit() == settings.FILE_SIZE_LIMIT

    @override_settings(FILE_SIZE_LIMIT=200 * MB, FILE_SIZE_LIMIT_MAX=100 * MB)
    def test_the_ceiling_never_sits_below_the_default(self, db):
        assert get_file_size_limit_max() == 200 * MB


@pytest.fixture
def issue(db, workspace, create_user):
    project = Project.objects.create(name="P", identifier="P", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)
    return Issue.objects.create(name="I", workspace=workspace, project=project, state=state, created_by=create_user)


@pytest.mark.contract
@pytest.mark.django_db
@mock.patch("plane.app.views.issue.attachment.S3Storage")
class TestNewUploads:
    def attach(self, client, workspace, issue, size):
        url = f"/api/assets/v2/workspaces/{workspace.slug}/projects/{issue.project_id}/issues/{issue.id}/attachments/"
        return client.post(url, {"name": "big.bin", "type": "application/octet-stream", "size": size}, format="json")

    def test_the_announced_size_is_clamped_to_the_saved_limit(self, s3, session_client, workspace, issue, setting):
        s3.return_value.generate_presigned_post.return_value = {}
        setting.value = str(12 * MB)
        setting.save()
        response = self.attach(session_client, workspace, issue, 50 * MB)
        assert response.status_code == 200, response.data
        assert FileAsset.objects.get(id=response.data["asset_id"]).size == 12 * MB
        assert s3.return_value.generate_presigned_post.call_args.kwargs["file_size"] == 12 * MB

    def test_lowering_the_limit_leaves_stored_files_alone(self, s3, session_client, workspace, issue, setting):
        s3.return_value.generate_presigned_post.return_value = {}
        setting.value = str(40 * MB)
        setting.save()
        big = self.attach(session_client, workspace, issue, 30 * MB)
        assert FileAsset.objects.get(id=big.data["asset_id"]).size == 30 * MB

        setting.value = str(5 * MB)
        setting.save()
        stored = FileAsset.objects.get(id=big.data["asset_id"])
        assert stored.size == 30 * MB and not stored.is_deleted
        # a new upload of the same size is now clamped
        again = self.attach(session_client, workspace, issue, 30 * MB)
        assert FileAsset.objects.get(id=again.data["asset_id"]).size == 5 * MB


IMPORT_FILE = "IMPORT_FILE_SIZE_LIMIT"
IMPORT_ITEMS = "IMPORT_MAX_WORK_ITEMS"


@pytest.fixture
def import_settings(db):
    return [
        InstanceConfiguration.objects.create(key=key, value="", category="WORKSPACE_MANAGEMENT")
        for key in (IMPORT_FILE, IMPORT_ITEMS)
    ]


@pytest.mark.contract
@pytest.mark.django_db
class TestImportLimits:
    def test_the_defaults_are_reported(self, session_client, instance_admin, import_settings):
        config = session_client.get(INSTANCE).data["config"]
        assert config["import_file_size_limit"] == 15 * MB
        assert config["import_max_work_items"] == 500
        assert config["import_max_work_items_max"] == 5000

    def test_both_can_be_saved_and_are_reported(self, session_client, instance_admin, import_settings):
        response = session_client.patch(
            CONFIGURATIONS, {IMPORT_FILE: str(40 * MB), IMPORT_ITEMS: "2000"}, format="json"
        )
        assert response.status_code == 200, response.data
        config = session_client.get(INSTANCE).data["config"]
        assert config["import_file_size_limit"] == 40 * MB
        assert config["import_max_work_items"] == 2000

    @pytest.mark.parametrize(
        "payload",
        [
            {IMPORT_FILE: "abc"},
            {IMPORT_FILE: str(MIN_FILE_SIZE_LIMIT - 1)},
            {IMPORT_FILE: str(get_file_size_limit_max() + 1)},
            {IMPORT_ITEMS: "0"},
            {IMPORT_ITEMS: "5001"},
            {IMPORT_ITEMS: "ten"},
        ],
    )
    def test_values_out_of_range_are_refused(self, session_client, instance_admin, import_settings, payload):
        assert session_client.patch(CONFIGURATIONS, payload, format="json").status_code == 400
        assert all(setting.value == "" for setting in InstanceConfiguration.objects.filter(key__in=payload))

    def test_empty_goes_back_to_the_defaults(self, session_client, instance_admin, import_settings):
        session_client.patch(CONFIGURATIONS, {IMPORT_FILE: str(40 * MB), IMPORT_ITEMS: "2000"}, format="json")
        assert (
            session_client.patch(CONFIGURATIONS, {IMPORT_FILE: "", IMPORT_ITEMS: ""}, format="json").status_code == 200
        )
        config = session_client.get(INSTANCE).data["config"]
        assert config["import_file_size_limit"] == 15 * MB and config["import_max_work_items"] == 500


@pytest.mark.contract
@pytest.mark.django_db
class TestImportUsesTheLimits:
    def project(self, workspace, create_user):
        project = Project.objects.create(name="Imp", identifier="IMP", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)
        return project

    def post(self, client, workspace, project, rows):
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv = "Name\n" + "\n".join(f"item {i}" for i in range(rows)) + "\n"
        return client.post(
            f"/api/workspaces/{workspace.slug}/import-work-items/",
            {"file": SimpleUploadedFile("w.csv", csv.encode()), "project_id": str(project.id), "provider": "csv"},
            format="multipart",
        )

    def test_the_number_of_work_items_follows_the_setting(
        self, session_client, workspace, create_user, import_settings
    ):
        project = self.project(workspace, create_user)
        import_settings[1].value = "3"
        import_settings[1].save()
        refused = self.post(session_client, workspace, project, 4)
        assert refused.status_code == 400
        assert "3 work items" in str(refused.data)
        assert self.post(session_client, workspace, project, 3).status_code in (200, 201)

    def test_the_file_size_follows_the_setting(self, session_client, workspace, create_user, import_settings):
        project = self.project(workspace, create_user)
        import_settings[0].value = str(MIN_FILE_SIZE_LIMIT)
        import_settings[0].save()
        csv_rows = 200000
        refused = self.post(session_client, workspace, project, csv_rows)
        assert refused.status_code == 400
        assert "MB" in str(refused.data)
