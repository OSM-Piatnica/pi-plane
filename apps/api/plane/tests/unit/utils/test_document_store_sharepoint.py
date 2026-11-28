# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The SharePoint document store against a fake Microsoft Graph.

``FakeLibrary`` plays one document library: upload sessions, files with versions, eTags and cTags, download URLs and
thumbnails. The browser's part (sending the bytes to the upload session) is played by ``FakeLibrary.upload``. All of
it follows Microsoft's documentation; none of it has been checked against a real tenant (B1).
"""

import hashlib
import json
from urllib.parse import unquote

import httpx
import pytest

from plane.bgtasks.document_checksum_task import compute_sha256
from plane.db.models.document import Document, DocumentLibrary, DocumentProvider, DocumentVersion
from plane.utils.document_store.base import (
    DocumentStoreError,
    FileMissingError,
    FileTooLargeError,
    NameTakenError,
    StoreNotConfiguredError,
    UploadIncompleteError,
    UploadRequest,
    changed_since,
)
from plane.utils.document_store.sharepoint import (
    UPLOAD_CHUNK_MULTIPLE,
    SharePointStore,
    default_folder,
    sharepoint_file_name,
)
from plane.utils.sharepoint.client import SharePointClient, pre_authenticated_url
from plane.utils.sharepoint.errors import SharePointConfigurationError, SharePointTransportError

pytestmark = pytest.mark.unit

TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "6731de76-14a6-49ae-97bc-6eba6914391e"
SECRET = "s3cr3t~Value.That-Must_Not.Leak"
DRIVE_ID = "b!BCZxLHAT50Sh9UJlc_2nucNEIi0aJepJk6g54cOgYP4"
SP = "https://contoso.sharepoint.com"


class FakeCache:
    def __init__(self):
        self.entries = {}

    def get(self, key):
        return self.entries.get(key)

    def set(self, key, value, timeout):
        self.entries[key] = value

    def delete(self, key):
        self.entries.pop(key, None)


class FakeLibrary:
    """One SharePoint document library as Graph shows it."""

    def __init__(self):
        self.items = {}  # id -> {"path", "versions": [bytes, ...], "etag_n"}
        self.sessions = {}  # n -> {"path"} or {"item_id"}
        self.requests = []
        self.graph_answers = []  # answers to give before the normal ones (errors)

    # -- the browser's part, and a person editing in SharePoint
    def upload(self, upload_url, content: bytes):
        number = int(upload_url.rsplit("/", 1)[1])
        session = self.sessions.pop(number)
        if "item_id" in session:
            self._new_version(session["item_id"], content)
        else:
            item_id = f"01ITEM{len(self.items) + 1:04d}"
            self.items[item_id] = {"path": session["path"], "versions": [content], "meta": 1}

    def edit_in_sharepoint(self, item_id, content: bytes):
        self._new_version(item_id, content)

    def rename_in_sharepoint(self, item_id, name):
        item = self.items[item_id]
        folder = item["path"].rsplit("/", 1)[0]
        item["path"] = f"{folder}/{name}"
        item["meta"] += 1

    def _new_version(self, item_id, content):
        item = self.items[item_id]
        item["versions"].append(content)
        item["meta"] += 1

    # -- Graph
    def _item_json(self, item_id, *, download=False):
        item = self.items[item_id]
        version = len(item["versions"])
        data = {
            "id": item_id,
            "name": item["path"].rsplit("/", 1)[1],
            "webUrl": f"{SP}/sites/Projects/Shared%20Documents/{item['path']}",
            "eTag": f'"{{{item_id}}},{item["meta"]}"',
            "cTag": f'"c:{{{item_id}}},{version}"',
            "size": len(item["versions"][-1]),
            "file": {"mimeType": "application/pdf"},
            "parentReference": {"driveId": DRIVE_ID, "path": f"/drive/root:/{item['path'].rsplit('/', 1)[0]}"},
        }
        if download:
            data["@microsoft.graph.downloadUrl"] = f"{SP}/download/{item_id}/current?tempauth=xyz"
        return data

    def _by_path(self, path):
        return next((item_id for item_id, item in self.items.items() if item["path"] == path), None)

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        host = request.url.host
        if host == "login.microsoftonline.com":
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        path = unquote(request.url.path)
        if host.endswith(".sharepoint.com"):
            assert "Authorization" not in request.headers, "a pre-authenticated URL must not get the token"
            _, kind, item_id, which = path.split("/")
            assert kind == "download"
            item = self.items[item_id]
            content = item["versions"][-1] if which.startswith("current") else item["versions"][int(which) - 1]
            return httpx.Response(200, content=content)
        assert host == "graph.microsoft.com"
        if self.graph_answers:
            return self.graph_answers.pop(0)
        route = path.removeprefix("/v1.0")
        drive_prefix = f"/drives/{DRIVE_ID}"
        assert route.startswith(drive_prefix), route
        route = route[len(drive_prefix) :]
        if route.startswith("/root:/") and route.endswith(":/createUploadSession"):
            target = route[len("/root:/") : -len(":/createUploadSession")]
            body = json.loads(request.content)
            assert body == {"item": {"@microsoft.graph.conflictBehavior": "fail"}}
            if self._by_path(target):
                return httpx.Response(409, json={"error": {"code": "nameAlreadyExists", "message": "exists"}})
            return self._session({"path": target})
        if route.startswith("/root:/"):
            item_id = self._by_path(route[len("/root:/") :])
            if item_id is None:
                return httpx.Response(404, json={"error": {"code": "itemNotFound", "message": "nope"}})
            return httpx.Response(200, json=self._item_json(item_id))
        parts = route.split("/")  # "", "items", id, ...
        item_id = parts[2]
        if item_id not in self.items:
            return httpx.Response(404, json={"error": {"code": "itemNotFound", "message": "nope"}})
        rest = parts[3:]
        if not rest:
            select = request.url.params.get("$select", "")
            return httpx.Response(200, json=self._item_json(item_id, download="downloadUrl" in select))
        if rest == ["createUploadSession"]:
            assert json.loads(request.content) == {"item": {"@microsoft.graph.conflictBehavior": "replace"}}
            return self._session({"item_id": item_id})
        if rest == ["versions"]:
            count = len(self.items[item_id]["versions"])
            value = [
                {"id": f"{n}.0", "size": len(self.items[item_id]["versions"][n - 1]), "lastModifiedDateTime": "x"}
                for n in range(count, 0, -1)
            ]
            return httpx.Response(200, json={"value": value})
        if rest[0] == "versions" and rest[2:] == ["content"]:
            number = int(rest[1].split(".")[0])
            return httpx.Response(302, headers={"Location": f"{SP}/download/{item_id}/{number}?tempauth=abc"})
        if rest == ["thumbnails", "0", "medium"]:
            return httpx.Response(200, json={"url": "https://westeurope1-mediap.svc.ms/transform/thumbnail?x=1"})
        raise AssertionError(f"unexpected Graph call {request.method} {route}")

    def _session(self, session):
        number = len(self.sessions) + 100
        self.sessions[number] = session
        return httpx.Response(
            200,
            json={"uploadUrl": f"{SP}/_api/v2.0/uploadSession/{number}", "expirationDateTime": "2026-11-30T12:00:00Z"},
        )


@pytest.fixture
def library():
    return FakeLibrary()


@pytest.fixture
def store(library):
    cache = FakeCache()

    def factory(**options):
        return SharePointClient(
            TENANT, CLIENT_ID, SECRET, transport=httpx.MockTransport(library), cache=cache, sleep=lambda s: None
        )

    return SharePointStore(
        library=DocumentLibrary(drive_id=DRIVE_ID, root_path="Pi-Plane/Docs", provider=DocumentProvider.SHAREPOINT),
        client_factory=factory,
        max_file_size=1000,
    )


def _new(name="Label front.pdf", size=5):
    return UploadRequest(
        workspace_id="w",
        name=name,
        mime_type="application/pdf",
        size=size,
        folder=default_folder("PACK", 7),
    )


def _document(stored):
    return Document(
        name=stored.name,
        mime_type="application/pdf",
        provider=DocumentProvider.SHAREPOINT,
        external_drive_id=stored.external_drive_id,
        external_item_id=stored.external_item_id,
    )


def _version(stored, number=1, content=b""):
    return DocumentVersion(
        number=number,
        mime_type="application/pdf",
        size=stored.size,
        etag=stored.etag,
        content_tag=stored.content_tag,
        external_version_id=stored.external_version_id,
        sha256=hashlib.sha256(content).hexdigest() if content else "",
    )


def _upload_new(store, library, content=b"v1pdf", name="Label front.pdf"):
    planned = store.begin_upload(_new(name=name, size=len(content)))
    library.upload(planned.target.url, content)
    return store.finish_upload(planned.state, size=len(content))


class TestNames:
    def test_forbidden_characters_become_underscores(self):
        assert sharepoint_file_name('a:b*c?"d<e>f|g/h\\i#j%k.pdf') == "a_b_c__d_e_f_g_h_i_j_k.pdf"

    def test_trailing_dots_and_spaces_are_dropped(self):
        assert sharepoint_file_name("  report.pdf. . ") == "report.pdf"

    def test_reserved_names_and_prefixes_are_escaped(self):
        assert sharepoint_file_name("CON.pdf") == "_CON.pdf"
        assert sharepoint_file_name("~$draft.docx") == "_draft.docx"
        assert sharepoint_file_name("desktop.ini") == "_desktop.ini"

    def test_a_long_name_keeps_its_extension(self):
        name = sharepoint_file_name("x" * 400 + ".pdf")
        assert len(name) == 200
        assert name.endswith("x.pdf")

    def test_an_empty_name_falls_back(self):
        assert sharepoint_file_name(" ... ") == "document"

    def test_the_default_folder_follows_the_plan(self):
        assert default_folder("PACK", 12) == ("PACK", "PACK-12")
        assert default_folder("PACK") == ("PACK",)


class TestNewDocument:
    def test_begin_asks_for_a_session_at_the_default_path_and_hands_it_to_the_browser(self, store, library):
        planned = store.begin_upload(_new())
        (_token, call) = library.requests
        assert unquote(call.url.path) == (
            f"/v1.0/drives/{DRIVE_ID}/root:/Pi-Plane/Docs/PACK/PACK-7/Label front.pdf:/createUploadSession"
        )
        target = planned.target
        assert target.kind == "upload_session"
        assert target.method == "PUT"
        assert target.url.startswith(f"{SP}/_api/v2.0/uploadSession/")
        assert target.chunk_multiple == UPLOAD_CHUNK_MULTIPLE
        assert target.chunk_size % UPLOAD_CHUNK_MULTIPLE == 0
        # The pre-authenticated address is not in the state that goes into the upload token, nor in a repr
        assert target.url not in json.dumps(planned.state)
        assert target.url not in repr(planned)
        assert planned.state == {
            "drive_id": DRIVE_ID,
            "path": "Pi-Plane/Docs/PACK/PACK-7/Label front.pdf",
            "name": "Label front.pdf",
        }

    def test_finish_reads_back_the_item_and_its_current_version(self, store, library):
        stored = _upload_new(store, library)
        assert stored.external_item_id == "01ITEM0001"
        assert stored.external_drive_id == DRIVE_ID
        assert stored.external_version_id == "1.0"
        assert stored.size == 5
        assert stored.name == "Label front.pdf"
        assert stored.content_tag and stored.etag
        assert stored.web_url.startswith(f"{SP}/sites/Projects/")

    def test_finish_before_the_bytes_arrived_is_incomplete(self, store):
        planned = store.begin_upload(_new())
        with pytest.raises(UploadIncompleteError):
            store.finish_upload(planned.state, size=5)

    def test_a_different_size_is_incomplete(self, store, library):
        planned = store.begin_upload(_new(size=5))
        library.upload(planned.target.url, b"longer than five")
        with pytest.raises(UploadIncompleteError) as caught:
            store.finish_upload(planned.state, size=5)
        assert caught.value.code == "size_mismatch"

    def test_an_existing_file_of_the_same_name_is_never_overwritten(self, store, library):
        _upload_new(store, library)
        with pytest.raises(NameTakenError) as caught:
            store.begin_upload(_new())
        assert caught.value.http_status == 409

    def test_a_file_larger_than_the_limit_is_refused_before_asking_graph(self, store, library):
        with pytest.raises(FileTooLargeError):
            store.begin_upload(_new(size=1001))
        assert library.requests == []

    def test_without_a_library_a_new_document_cannot_go_to_sharepoint(self, store):
        store.library = None
        with pytest.raises(StoreNotConfiguredError):
            store.begin_upload(_new())


class TestNewVersion:
    def test_a_new_version_replaces_the_content_of_the_same_file(self, store, library):
        first = _upload_new(store, library)
        request = UploadRequest(
            workspace_id="w",
            name=first.name,
            mime_type="application/pdf",
            size=6,
            drive_id=first.external_drive_id,
            item_id=first.external_item_id,
            base_content_tag=first.content_tag,
        )
        planned = store.begin_upload(request)
        assert unquote(library.requests[-1].url.path).endswith(f"/items/{first.external_item_id}/createUploadSession")
        # Nothing arrived yet: the content tag is the old one
        with pytest.raises(UploadIncompleteError):
            store.finish_upload(planned.state, size=6)
        library.upload(planned.target.url, b"v2-pdf")
        second = store.finish_upload(planned.state, size=6)
        assert second.external_item_id == first.external_item_id
        assert second.external_version_id == "2.0"
        assert second.content_tag != first.content_tag


class TestReading:
    def test_the_current_version_downloads_through_the_items_download_url(self, store, library):
        stored = _upload_new(store, library)
        url = store.download_url(_document(stored), _version(stored))
        assert url == f"{SP}/download/01ITEM0001/current?tempauth=xyz"

    def test_an_older_version_downloads_by_its_version_id(self, store, library):
        stored = _upload_new(store, library, content=b"v1pdf")
        library.edit_in_sharepoint(stored.external_item_id, b"edited")
        document, version = _document(stored), _version(stored, content=b"v1pdf")
        assert store.download_url(document, version) == f"{SP}/download/01ITEM0001/1?tempauth=abc"
        # The checksum check reads exactly the bytes of that version, without the token
        assert compute_sha256(store.open_stream(document, version)) == (hashlib.sha256(b"v1pdf").hexdigest(), 5)

    def test_a_change_in_sharepoint_shows_in_the_live_state(self, store, library):
        stored = _upload_new(store, library)
        document, version = _document(stored), _version(stored)
        assert not changed_since(version, store.live_state(document))
        library.edit_in_sharepoint(stored.external_item_id, b"edited!")
        assert changed_since(version, store.live_state(document))
        current = store.current_file(document)
        assert current.external_version_id == "2.0"
        assert current.size == 7

    def test_a_rename_alone_is_not_a_change_of_content(self, store, library):
        stored = _upload_new(store, library)
        library.rename_in_sharepoint(stored.external_item_id, "Renamed.pdf")
        live = store.live_state(_document(stored))
        assert live.etag != stored.etag
        assert not changed_since(_version(stored), live)

    def test_the_thumbnail_is_a_short_lived_address(self, store, library):
        stored = _upload_new(store, library)
        assert store.thumbnail_url(_document(stored)).startswith("https://westeurope1-mediap.svc.ms/")

    def test_versions_are_listed_newest_first(self, store, library):
        stored = _upload_new(store, library)
        library.edit_in_sharepoint(stored.external_item_id, b"edited")
        assert [version.id for version in store.list_versions(_document(stored))] == ["2.0", "1.0"]

    def test_a_file_deleted_in_sharepoint_is_missing(self, store, library):
        stored = _upload_new(store, library)
        library.items.clear()
        with pytest.raises(FileMissingError):
            store.live_state(_document(stored))


class TestErrors:
    def test_switched_off_sharepoint_is_not_configured(self):
        def factory(**options):
            raise SharePointConfigurationError("SharePoint is switched off on this instance.", code="disabled")

        store = SharePointStore(client_factory=factory, max_file_size=10)
        with pytest.raises(StoreNotConfiguredError) as caught:
            store.live_state(Document(external_drive_id=DRIVE_ID, external_item_id="01ITEM0001"))
        assert caught.value.http_status == 409

    def test_throttling_is_passed_on_as_a_temporary_error(self, store, library):
        library.graph_answers = [
            httpx.Response(429, headers={"Retry-After": "120"}, json={"error": {"code": "tooMany"}})
        ] * 4
        with pytest.raises(DocumentStoreError) as caught:
            store.begin_upload(_new())
        assert caught.value.code == "throttled"
        assert caught.value.http_status == 503

    def test_a_root_folder_that_climbs_out_never_reaches_graph(self, store, library):
        store.library.root_path = "Docs/../../other"
        with pytest.raises(DocumentStoreError) as caught:
            store.begin_upload(_new())
        assert caught.value.code == "sharepoint_invalid_item_name"
        assert [request.url.host for request in library.requests] == []

    def test_a_download_url_outside_sharepoint_is_refused(self):
        with pytest.raises(SharePointTransportError):
            pre_authenticated_url("https://evil.example.com/download")
        with pytest.raises(SharePointTransportError):
            pre_authenticated_url("http://contoso.sharepoint.com/download")
        with pytest.raises(SharePointTransportError):
            pre_authenticated_url("https://user@contoso.sharepoint.com/download")
        assert pre_authenticated_url(f"{SP}/x") == f"{SP}/x"

    def test_a_version_redirect_to_another_host_is_refused(self, store, library):
        stored = _upload_new(store, library)
        library.edit_in_sharepoint(stored.external_item_id, b"edited")
        library.graph_answers = [
            httpx.Response(200, json=library._item_json(stored.external_item_id, download=True)),
            httpx.Response(302, headers={"Location": "https://evil.example.com/steal"}),
        ]
        with pytest.raises(DocumentStoreError):
            store.download_url(_document(stored), _version(stored))
