# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The native document store (Pi-Plane's own object storage) against an in-memory storage."""

import hashlib

import pytest

from plane.bgtasks.document_checksum_task import compute_sha256
from plane.db.models.document import Document, DocumentVersion
from plane.tests.document_storage_fake import FakeObjectStorage
from plane.utils.document_store.base import (
    FileTooLargeError,
    LiveState,
    UploadIncompleteError,
    UploadRequest,
    changed_since,
)
from plane.utils.document_store.native import NativeStore

pytestmark = pytest.mark.unit


def _request(size=8, name="Artwork v1.pdf"):
    return UploadRequest(workspace_id="ws-1", name=name, mime_type="application/pdf", size=size)


@pytest.fixture
def storage():
    return FakeObjectStorage()


@pytest.fixture
def store(storage):
    return NativeStore(storage=storage, max_file_size=100)


class TestUpload:
    def test_begin_gives_a_presigned_post_for_a_new_key_capped_at_the_size(self, store, storage):
        planned = store.begin_upload(_request())
        key = planned.state["storage_key"]
        assert key.startswith("ws-1/documents/") and key.endswith("-Artwork v1.pdf")
        assert planned.target.kind == "presigned_post"
        assert planned.target.fields["key"] == key
        assert storage.presigned_posts == [{"key": key, "type": "application/pdf", "size": 8}]

    def test_each_upload_gets_its_own_object(self, store):
        assert store.begin_upload(_request()).state != store.begin_upload(_request()).state

    def test_azure_answers_with_a_single_put(self):
        planned = NativeStore(storage=FakeObjectStorage(use_put=True), max_file_size=100).begin_upload(_request())
        assert planned.target.kind == "put"
        assert planned.target.method == "PUT"
        assert planned.target.headers["x-ms-blob-type"] == "BlockBlob"

    def test_finish_reads_the_metadata_of_the_object(self, store, storage):
        planned = store.begin_upload(_request())
        storage.put(planned.state["storage_key"], b"%PDF-1.7")
        stored = store.finish_upload(planned.state, size=8)
        assert stored.storage_key == planned.state["storage_key"]
        assert stored.size == 8
        assert stored.etag == "etag-8"
        assert stored.external_item_id == ""

    def test_finish_without_the_object_is_incomplete(self, store):
        planned = store.begin_upload(_request())
        with pytest.raises(UploadIncompleteError):
            store.finish_upload(planned.state, size=8)

    def test_an_object_of_another_size_is_removed(self, store, storage):
        planned = store.begin_upload(_request())
        storage.put(planned.state["storage_key"], b"much longer than announced")
        with pytest.raises(UploadIncompleteError) as caught:
            store.finish_upload(planned.state, size=8)
        assert caught.value.code == "size_mismatch"
        assert storage.deleted == [planned.state["storage_key"]]

    def test_a_file_over_the_limit_is_refused(self, store, storage):
        with pytest.raises(FileTooLargeError):
            store.begin_upload(_request(size=101))
        assert storage.presigned_posts == []

    def test_a_name_with_a_path_is_flattened(self, store):
        planned = store.begin_upload(_request(name="../../etc/passwd"))
        assert "/../" not in planned.state["storage_key"]


class TestReading:
    def test_download_is_a_presigned_url_of_the_versions_object(self, store):
        document = Document(name="Artwork.pdf", mime_type="application/pdf")
        version = DocumentVersion(number=1, storage_key="ws-1/documents/abc-Artwork.pdf", mime_type="application/pdf")
        url = store.download_url(document, version, disposition="inline")
        assert url.startswith("https://s3.example.test/uploads/ws-1/documents/abc-Artwork.pdf")

    def test_nothing_changes_outside_pi_plane(self, store):
        assert store.live_state(Document()) is None
        assert store.thumbnail_url(Document()) is None
        assert not changed_since(DocumentVersion(etag="a"), None)

    def test_open_stream_reads_the_whole_object(self, store, storage):
        storage.put("k", b"0123456789")
        computed = compute_sha256(store.open_stream(Document(), DocumentVersion(storage_key="k")))
        assert computed == (hashlib.sha256(b"0123456789").hexdigest(), 10)

    def test_versions_are_listed_from_the_records_newest_first(self, store):
        versions = [DocumentVersion(number=n, storage_key=f"k{n}", size=n) for n in (1, 3, 2)]
        assert [remote.id for remote in store.list_versions(Document(), versions)] == ["k3", "k2", "k1"]


class TestChangedSince:
    def test_the_content_tag_decides_when_both_have_one(self):
        version = DocumentVersion(etag="e1", content_tag="c1")
        assert not changed_since(version, LiveState(etag="e2", content_tag="c1", size=1))
        assert changed_since(version, LiveState(etag="e1", content_tag="c2", size=1))

    def test_the_etag_decides_without_a_content_tag(self):
        version = DocumentVersion(etag="e1")
        assert changed_since(version, LiveState(etag="e2", content_tag="", size=1))
        assert not changed_since(version, LiveState(etag="e1", content_tag="", size=1))
