# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Document libraries in the workspace settings and a project's choice of library and folder (B4).

Microsoft Graph is played by ``httpx.MockTransport`` under the real client, so the views use the client as in
production while nothing reaches a network. The answers follow Microsoft's documentation; none of this has been run
against a real tenant (B1).
"""

from unittest import mock
from urllib.parse import unquote

import httpx
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from plane.db.models import (
    DocumentLibrary,
    Project,
    ProjectDocumentSettings,
    ProjectMember,
    User,
    WorkspaceMember,
)
from plane.utils.sharepoint import config as sharepoint_config
from plane.utils.sharepoint.client import SharePointClient
from plane.utils.sharepoint.config import SharePointSettings

ADMIN, MEMBER = 20, 15
TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "6731de76-14a6-49ae-97bc-6eba6914391e"
SECRET = "s3cr3t~Value.That-Must_Not.Leak"
SITE_URL = "https://contoso.sharepoint.com/sites/Projects"
SITE_ID = "contoso.sharepoint.com,2c712604-1370-44e7-a1f5-426573fda7b9,2d2244c3-251a-49ea-93a8-39e1c3a060fe"
DRIVE_ID = "b!BCZxLHAT50Sh9UJlc_2nucNEIi0aJepJk6g54cOgYP4"
OTHER_DRIVE_ID = "b!OTHERxLHAT50Sh9UJlc_2nucNEIi0aJepJk6g54cOgYP4"
DRIVE_URL = "https://contoso.sharepoint.com/sites/Projects/Shared%20Documents"


class FakeGraph:
    """One site with two libraries; folders that exist in the first one; upload sessions that remember their path."""

    def __init__(self):
        self.requests = []
        self.folders = set()
        self.site_status = 200
        self.sessions = []

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        if request.url.host == "login.microsoftonline.com":
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        assert request.url.host == "graph.microsoft.com"
        route = unquote(request.url.path).removeprefix("/v1.0")
        if route == "/sites/contoso.sharepoint.com:/sites/Projects":
            if self.site_status != 200:
                return httpx.Response(self.site_status, json={"error": {"code": "x", "message": "no"}})
            return httpx.Response(200, json={"id": SITE_ID, "displayName": "Projects", "webUrl": SITE_URL})
        if route == f"/sites/{SITE_ID}/drives":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {"id": DRIVE_ID, "name": "Documents", "webUrl": DRIVE_URL, "driveType": "documentLibrary"},
                        {
                            "id": OTHER_DRIVE_ID,
                            "name": "Artwork",
                            "webUrl": f"{SITE_URL}/Artwork",
                            "driveType": "documentLibrary",
                        },
                    ]
                },
            )
        prefix = f"/drives/{DRIVE_ID}/root:/"
        if route.startswith(prefix) and route.endswith(":/createUploadSession"):
            path = route[len(prefix) : -len(":/createUploadSession")]
            self.sessions.append(path)
            return httpx.Response(
                200,
                json={
                    "uploadUrl": f"https://contoso.sharepoint.com/_api/v2.0/uploadSession/{len(self.sessions)}",
                    "expirationDateTime": "2026-11-30T12:00:00Z",
                },
            )
        if route.startswith(prefix):
            path = route[len(prefix) :]
            if path in self.folders:
                return httpx.Response(
                    200,
                    json={
                        "id": "01FOLDER",
                        "name": path.rsplit("/", 1)[-1],
                        "webUrl": f"{DRIVE_URL}/{path}",
                        "eTag": '"1"',
                        "folder": {"childCount": 0},
                    },
                )
            return httpx.Response(404, json={"error": {"code": "itemNotFound", "message": "nope"}})
        raise AssertionError(f"unexpected Graph call {request.method} {route}")


@pytest.fixture
def graph():
    return FakeGraph()


@pytest.fixture
def sharepoint(graph):
    """SharePoint switched on, with the real client talking to the fake Graph."""
    cache.clear()
    settings = SharePointSettings(enabled=True, tenant_id=TENANT, client_id=CLIENT_ID, client_secret=SECRET)

    def client(*args, **kwargs):
        kwargs.pop("transport", None)
        return SharePointClient(*args, transport=httpx.MockTransport(graph), sleep=lambda s: None, **kwargs)

    with (
        mock.patch.object(sharepoint_config, "get_sharepoint_settings", return_value=settings),
        mock.patch.object(sharepoint_config, "SharePointClient", side_effect=client),
    ):
        yield settings
    cache.clear()


@pytest.fixture
def sharepoint_off():
    settings = SharePointSettings(enabled=False, tenant_id="", client_id="", client_secret="")
    with mock.patch.object(sharepoint_config, "get_sharepoint_settings", return_value=settings):
        yield settings


@pytest.fixture(autouse=True)
def _no_background_jobs():
    with (
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
        mock.patch("plane.bgtasks.document_checksum_task.verify_document_version_checksum.delay"),
    ):
        yield


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Packaging", identifier="PACK", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _member(workspace, project=None, role=MEMBER, email="member@example.com"):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    if project is not None:
        ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return _client(user)


def _libraries(workspace):
    return f"/api/workspaces/{workspace.slug}/document-libraries/"


def _project_settings(project):
    return f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/document-settings/"


def _library(workspace, *, drive_id=DRIVE_ID, root_path="Pi-Plane", is_default=False, name="Documents"):
    return DocumentLibrary.objects.create(
        workspace=workspace,
        name=name,
        site_id=SITE_ID,
        drive_id=drive_id,
        root_path=root_path,
        web_url=DRIVE_URL,
        is_default=is_default,
    )


@pytest.mark.contract
class TestWorkspaceLibraries:
    def test_listing_says_when_sharepoint_is_not_set_up(self, session_client, workspace, sharepoint_off):
        response = session_client.get(_libraries(workspace))
        assert response.status_code == 200, response.data
        assert response.data["sharepoint_enabled"] is False
        assert response.data["default_provider"] == "native"
        assert response.data["native"] == {"is_default": True}
        assert response.data["libraries"] == []

    def test_looking_up_a_site_without_sharepoint_answers_not_configured(
        self, session_client, workspace, sharepoint_off
    ):
        response = session_client.post(f"{_libraries(workspace)}sites/", {"site_url": SITE_URL}, format="json")
        assert response.status_code == 400
        assert response.data["error_code"] == "not_configured"
        assert "God Mode" in response.data["error"]

    def test_looking_up_a_site_lists_its_libraries(self, session_client, workspace, sharepoint):
        _library(workspace, root_path="Pi-Plane")
        response = session_client.post(f"{_libraries(workspace)}sites/", {"site_url": SITE_URL}, format="json")
        assert response.status_code == 200, response.data
        assert response.data["site"] == {"id": SITE_ID, "name": "Projects", "web_url": SITE_URL}
        drives = {drive["id"]: drive for drive in response.data["drives"]}
        assert drives[DRIVE_ID]["name"] == "Documents"
        assert drives[DRIVE_ID]["used_root_paths"] == ["Pi-Plane"]
        assert drives[OTHER_DRIVE_ID]["used_root_paths"] == []

    def test_a_site_without_a_grant_says_what_to_do(self, session_client, workspace, sharepoint, graph):
        graph.site_status = 403
        response = session_client.post(f"{_libraries(workspace)}sites/", {"site_url": SITE_URL}, format="json")
        assert response.status_code == 400
        assert response.data["error_code"] == "site_access_denied"

    def test_an_address_outside_sharepoint_is_refused_before_graph(self, session_client, workspace, sharepoint, graph):
        response = session_client.post(
            f"{_libraries(workspace)}sites/", {"site_url": "https://example.com/sites/x"}, format="json"
        )
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_site_url"
        assert graph.requests == []

    def test_adding_stores_what_graph_confirms_and_the_first_becomes_default(
        self, session_client, workspace, sharepoint
    ):
        response = session_client.post(
            _libraries(workspace),
            {"site_url": SITE_URL, "drive_id": DRIVE_ID, "root_path": "/Pi-Plane/Docs/"},
            format="json",
        )
        assert response.status_code == 201, response.data
        library = DocumentLibrary.objects.get()
        assert (library.site_id, library.drive_id, library.root_path) == (SITE_ID, DRIVE_ID, "Pi-Plane/Docs")
        assert library.name == "Documents"
        assert library.web_url == DRIVE_URL
        assert library.is_default is True
        assert response.data["folder_web_url"] == f"{DRIVE_URL}/Pi-Plane/Docs"

        listing = session_client.get(_libraries(workspace)).data
        assert listing["default_provider"] == "sharepoint"
        assert listing["native"] == {"is_default": False}

    def test_adding_a_library_the_site_does_not_have_is_refused(self, session_client, workspace, sharepoint):
        response = session_client.post(
            _libraries(workspace), {"site_url": SITE_URL, "drive_id": "b!nothere"}, format="json"
        )
        assert response.status_code == 400
        assert response.data["error_code"] == "library_not_found"
        assert not DocumentLibrary.objects.exists()

    def test_the_same_folder_twice_is_refused(self, session_client, workspace, sharepoint):
        _library(workspace, root_path="Pi-Plane")
        response = session_client.post(
            _libraries(workspace), {"site_url": SITE_URL, "drive_id": DRIVE_ID, "root_path": "Pi-Plane"}, format="json"
        )
        assert response.status_code == 409
        assert response.data["error_code"] == "library_exists"

    def test_a_bad_root_folder_is_refused(self, session_client, workspace, sharepoint):
        response = session_client.post(
            _libraries(workspace), {"site_url": SITE_URL, "drive_id": DRIVE_ID, "root_path": "a:b"}, format="json"
        )
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_folder"

    def test_editing_name_folder_and_default(self, session_client, workspace, sharepoint_off):
        first = _library(workspace, is_default=True)
        second = _library(workspace, drive_id=OTHER_DRIVE_ID, root_path="", name="Artwork")
        url = f"{_libraries(workspace)}{second.id}/"
        response = session_client.patch(
            url, {"name": "Grafika", "root_path": "Opakowania", "is_default": True}, format="json"
        )
        assert response.status_code == 200, response.data
        second.refresh_from_db()
        first.refresh_from_db()
        assert (second.name, second.root_path, second.is_default) == ("Grafika", "Opakowania", True)
        assert first.is_default is False

    def test_pi_plane_storage_can_be_the_default(self, session_client, workspace, sharepoint_off):
        library = _library(workspace, is_default=True)
        response = session_client.post(f"{_libraries(workspace)}default/", {"library_id": None}, format="json")
        assert response.status_code == 200, response.data
        library.refresh_from_db()
        assert library.is_default is False
        response = session_client.post(
            f"{_libraries(workspace)}default/", {"library_id": str(library.id)}, format="json"
        )
        library.refresh_from_db()
        assert library.is_default is True

    def test_removing_sends_projects_back_to_the_workspace_default(self, session_client, workspace, project):
        library = _library(workspace)
        ProjectDocumentSettings.objects.create(project=project, store="sharepoint", library=library, folder="X")
        response = session_client.delete(f"{_libraries(workspace)}{library.id}/")
        assert response.status_code == 204
        assert not DocumentLibrary.objects.exists()
        settings = ProjectDocumentSettings.objects.get(project=project)
        assert (settings.store, settings.library_id, settings.folder) == ("workspace", None, "X")

    def test_only_workspace_admins(self, workspace, sharepoint_off):
        member = _member(workspace)
        assert member.get(_libraries(workspace)).status_code == 403
        assert member.post(f"{_libraries(workspace)}sites/", {"site_url": SITE_URL}).status_code == 403
        assert member.post(f"{_libraries(workspace)}default/", {"library_id": None}, format="json").status_code == 403


@pytest.mark.contract
class TestProjectDocumentSettings:
    def test_defaults_follow_the_workspace(self, session_client, workspace, project, sharepoint):
        _library(workspace, is_default=True, root_path="Pi-Plane")
        response = session_client.get(_project_settings(project))
        assert response.status_code == 200, response.data
        data = response.data
        assert (data["store"], data["library_id"], data["folder"]) == ("workspace", None, "")
        assert data["default_folder"] == "PACK"
        assert data["can_edit"] is True
        assert data["effective"]["provider"] == "sharepoint"
        assert data["effective"]["folder"] == "Pi-Plane/PACK"
        assert data["effective"]["folder_web_url"] == f"{DRIVE_URL}/Pi-Plane/PACK"

    def test_without_sharepoint_documents_stay_in_pi_plane(self, session_client, workspace, project, sharepoint_off):
        _library(workspace, is_default=True)
        data = session_client.get(_project_settings(project)).data
        assert data["sharepoint_enabled"] is False
        assert data["effective"]["provider"] == "native"
        assert data["effective"]["native_reason"] == "sharepoint_off"

    def test_choosing_a_library_and_folder(self, session_client, workspace, project, sharepoint):
        _library(workspace, is_default=True)
        other = _library(workspace, drive_id=OTHER_DRIVE_ID, root_path="", name="Artwork")
        response = session_client.put(
            _project_settings(project),
            {"store": "sharepoint", "library_id": str(other.id), "folder": "/Klienci/ACME/"},
            format="json",
        )
        assert response.status_code == 200, response.data
        settings = ProjectDocumentSettings.objects.get(project=project)
        assert (settings.store, settings.library_id, settings.folder) == ("sharepoint", other.id, "Klienci/ACME")
        assert response.data["effective"]["library"]["id"] == str(other.id)
        assert response.data["effective"]["folder"] == "Klienci/ACME"

    def test_pi_plane_storage_drops_the_folder(self, session_client, project, sharepoint):
        response = session_client.put(_project_settings(project), {"store": "native", "folder": "X"}, format="json")
        assert response.status_code == 200, response.data
        assert ProjectDocumentSettings.objects.get(project=project).folder == ""
        assert response.data["effective"]["provider"] == "native"

    def test_refuses_a_library_of_another_workspace_and_bad_values(self, session_client, project, sharepoint):
        response = session_client.put(
            _project_settings(project), {"store": "sharepoint", "library_id": None}, format="json"
        )
        assert response.data["error_code"] == "invalid_library"
        response = session_client.put(_project_settings(project), {"store": "elsewhere"}, format="json")
        assert response.data["error_code"] == "invalid_store"
        response = session_client.put(_project_settings(project), {"folder": "a|b"}, format="json")
        assert response.data["error_code"] == "invalid_folder"

    def test_members_read_and_admins_change(self, workspace, project, sharepoint_off):
        member = _member(workspace, project)
        response = member.get(_project_settings(project))
        assert response.status_code == 200
        assert response.data["can_edit"] is False
        assert member.put(_project_settings(project), {"store": "native"}, format="json").status_code == 403

    def test_new_documents_go_to_the_chosen_folder(self, session_client, workspace, project, sharepoint, graph):
        _library(workspace, is_default=True, root_path="Pi-Plane")
        ProjectDocumentSettings.objects.create(project=project, folder="Klienci/ACME")
        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/documents/uploads/",
            {"name": "Label.pdf", "type": "application/pdf", "size": 5},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["provider"] == "sharepoint"
        assert graph.sessions == ["Pi-Plane/Klienci/ACME/Label.pdf"]


@pytest.mark.contract
class TestProjectFolder:
    def test_an_existing_folder_answers_its_address(self, session_client, workspace, project, sharepoint, graph):
        _library(workspace, is_default=True, root_path="Pi-Plane")
        graph.folders.add("Pi-Plane/PACK")
        response = session_client.get(f"{_project_settings(project)}folder/")
        assert response.status_code == 200, response.data
        assert response.data == {"exists": True, "web_url": f"{DRIVE_URL}/Pi-Plane/PACK", "folder": "Pi-Plane/PACK"}

    def test_a_folder_not_made_yet_answers_the_root_folder(self, session_client, workspace, project, sharepoint):
        _library(workspace, is_default=True, root_path="Pi-Plane")
        response = session_client.get(f"{_project_settings(project)}folder/")
        assert response.status_code == 200, response.data
        assert response.data["exists"] is False
        assert response.data["web_url"] == f"{DRIVE_URL}/Pi-Plane"

    def test_pi_plane_storage_has_no_folder(self, session_client, project, sharepoint):
        response = session_client.get(f"{_project_settings(project)}folder/")
        assert response.status_code == 400
        assert response.data["error_code"] == "not_sharepoint"

    def test_sharepoint_off_says_so(self, session_client, workspace, project, sharepoint_off):
        _library(workspace, is_default=True)
        response = session_client.get(f"{_project_settings(project)}folder/")
        assert response.status_code == 400
        assert response.data["error_code"] == "not_configured"
