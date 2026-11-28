# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The native document store: Pi-Plane's own object storage (S3 and compatible, or Azure Blob Storage, whatever
``get_storage`` gives), one object per version. Uploads and downloads use presigned addresses exactly as work item
attachments do, so nothing new is needed from the storage or its CORS settings.

Objects are never overwritten or changed: each version has its own key, so ``live_state`` is always None.
"""

from uuid import uuid4

from plane.db.models.document import DocumentProvider
from plane.utils.file_size_limit import get_file_size_limit
from plane.utils.path_validator import sanitize_filename

from .base import (
    DocumentStore,
    DocumentStoreError,
    FileMissingError,
    FileTooLargeError,
    PlannedUpload,
    RemoteVersion,
    StoredFile,
    UploadIncompleteError,
    UploadRequest,
    UploadTarget,
)

READ_CHUNK_SIZE = 1024 * 1024


def _strip_quotes(value) -> str:
    return str(value or "").strip().strip('"')


class NativeStore(DocumentStore):
    provider = DocumentProvider.NATIVE

    def __init__(self, *, storage=None, request=None, max_file_size: int | None = None):
        # The storage is made on first use: S3 and Azure clients are not free to build
        self._storage = storage
        self._request = request
        self._max_file_size = max_file_size

    @property
    def storage(self):
        if self._storage is None:
            from plane.settings.storage import get_storage

            self._storage = get_storage(request=self._request)
        return self._storage

    def max_file_size(self) -> int:
        return self._max_file_size if self._max_file_size is not None else get_file_size_limit()

    def begin_upload(self, request: UploadRequest) -> PlannedUpload:
        if request.size > self.max_file_size():
            raise FileTooLargeError("The file is larger than this instance accepts.")
        name = sanitize_filename(request.name) or "document"
        key = f"{request.workspace_id}/documents/{uuid4().hex}-{name}"
        presigned = self.storage.generate_presigned_post(
            object_name=key, file_type=request.mime_type, file_size=request.size
        )
        if not presigned:
            raise DocumentStoreError("The storage did not give an address to upload to.", code="storage_error")
        if str(presigned.get("method") or "").upper() == "PUT":
            target = UploadTarget(
                kind="put", url=presigned["url"], method="PUT", headers=dict(presigned.get("headers") or {})
            )
        else:
            target = UploadTarget(
                kind="presigned_post", url=presigned["url"], method="POST", fields=dict(presigned.get("fields") or {})
            )
        return PlannedUpload(target=target, state={"storage_key": key, "name": name})

    def finish_upload(self, state: dict, *, size: int) -> StoredFile:
        key = str(state.get("storage_key") or "")
        if not key:
            raise UploadIncompleteError("This upload cannot be finished.")
        metadata = self.storage.get_object_metadata(object_name=key)
        if not metadata:
            raise UploadIncompleteError("The file has not arrived in the storage yet.")
        stored_size = metadata.get("ContentLength")
        if stored_size != size:
            # Azure cannot cap the size of a signed upload, so a different size is caught (and removed) here
            self.storage.delete_files([key])
            raise UploadIncompleteError(
                "The stored file is not the size that was announced.", code="size_mismatch", detail=str(stored_size)
            )
        return StoredFile(
            name=str(state.get("name") or ""),
            size=int(stored_size),
            etag=_strip_quotes(metadata.get("ETag")),
            content_tag=_strip_quotes(metadata.get("ETag")),
            storage_key=key,
        )

    def download_url(self, document, version, *, disposition: str = "attachment") -> str:
        url = self.storage.generate_presigned_url(
            object_name=version.storage_key,
            disposition=disposition,
            filename=document.name,
            content_type=version.mime_type,
        )
        if not url:
            raise DocumentStoreError("The storage did not give an address to download from.", code="storage_error")
        return url

    def thumbnail_url(self, document) -> str | None:
        # The browser renders the first page itself (C2)
        return None

    def list_versions(self, document, versions=()) -> list[RemoteVersion]:
        ordered = sorted(versions, key=lambda version: version.number, reverse=True)
        return [RemoteVersion(id=version.storage_key, size=version.size) for version in ordered]

    def live_state(self, document):
        return None

    def open_stream(self, document, version):
        if not version.storage_key:
            raise FileMissingError("This version has no stored file.")
        yield from self.storage.iter_object(version.storage_key, chunk_size=READ_CHUNK_SIZE)
