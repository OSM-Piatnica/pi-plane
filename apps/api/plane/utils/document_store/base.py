# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
What every document store does, whatever keeps the bytes.

A store moves bytes and reads metadata; it never touches the database. Recording documents and versions,
permissions and the upload token are the job of ``plane.utils.document_store.service`` and the views.

How bytes travel. Today both stores hand the browser a pre-authenticated address (``UploadTarget``, a download URL)
and the bytes go directly between the browser and the storage, as attachments do. For SharePoint that is
**unverified**: B1 must show that the browser may upload to a Graph upload session and fetch a download URL across
origins (CORS). If it may not, the SharePoint store answers ``begin_upload`` with an ``UploadTarget`` of kind
``proxy`` and the API streams the bytes itself (``open_stream`` already reads them for the checksum check); the
interface and the views do not change, only how the browser follows the target.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


class DocumentStoreError(Exception):
    """
    Something a store could not do. ``code`` is a short stable word the API hands to the browser next to the message;
    ``http_status`` is the status the API answers with. The message is written by Pi-Plane and safe to show.
    """

    code = "document_store_error"
    http_status = 502

    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None, detail: str = ""):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status
        # What the storage itself said, for the logs; never shown to people
        self.detail = detail


class StoreNotConfiguredError(DocumentStoreError):
    """The store this document needs is not set up or is switched off (SharePoint after it was turned off)."""

    code = "not_configured"
    http_status = 409


class UploadIncompleteError(DocumentStoreError):
    """The bytes are not (all) in the storage, or not the size that was announced."""

    code = "upload_incomplete"
    http_status = 400


class FileTooLargeError(DocumentStoreError):
    code = "file_too_large"
    http_status = 400


class NameTakenError(DocumentStoreError):
    """A file of this name is already in the folder, and a new document never overwrites it."""

    code = "name_taken"
    http_status = 409


class FileMissingError(DocumentStoreError):
    """The file or the version is no longer in the storage (deleted, or trimmed by a retention policy)."""

    code = "file_missing"
    http_status = 404


@dataclass(frozen=True)
class UploadRequest:
    """
    What is to be uploaded. ``folder`` is the folder under the library's root (SharePoint) for a new document;
    ``item_id`` and ``drive_id`` name the existing file when this is a new version of a document;
    ``base_content_tag`` is the content tag of its latest recorded version (to tell later whether bytes arrived).
    """

    workspace_id: str
    name: str
    mime_type: str
    size: int
    folder: tuple[str, ...] = ()
    drive_id: str = ""
    item_id: str = ""
    base_content_tag: str = ""


@dataclass(frozen=True)
class UploadTarget:
    """
    Where and how the browser sends the bytes.

    - ``presigned_post``: an HTML form POST to ``url`` with ``fields`` and the file last (S3 and compatible);
    - ``put``: one ``PUT`` of the whole file to ``url`` with ``headers`` (Azure Blob Storage);
    - ``upload_session``: ``PUT`` the file to ``url`` in consecutive ranges (``Content-Range``) of at most
      ``chunk_size`` bytes, each a multiple of ``chunk_multiple`` except the last (a Microsoft Graph upload session);
    - ``proxy`` (reserved, not used yet): send the bytes to the API, which passes them on.

    ``url`` is pre-authenticated and short-lived; it is kept out of repr and never stored.
    """

    kind: str
    url: str = field(repr=False)
    method: str = "POST"
    fields: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    expires_at: str = ""
    chunk_size: int | None = None
    chunk_multiple: int | None = None

    def as_dict(self) -> dict:
        data = {
            "kind": self.kind,
            "url": self.url,
            "method": self.method,
            "fields": self.fields,
            "headers": self.headers,
            "expires_at": self.expires_at or None,
        }
        if self.chunk_size:
            data["chunk_size"] = self.chunk_size
            data["chunk_multiple"] = self.chunk_multiple
        return data


@dataclass(frozen=True)
class PlannedUpload:
    """The target for the browser, and what the store needs to finish the upload (plain JSON, kept by the caller)."""

    target: UploadTarget
    state: dict


@dataclass(frozen=True)
class StoredFile:
    """What the store says about the bytes of a version once they are stored."""

    name: str
    size: int
    etag: str = ""
    content_tag: str = ""
    storage_key: str = ""
    external_drive_id: str = ""
    external_item_id: str = ""
    external_version_id: str = ""
    web_url: str = ""


@dataclass(frozen=True)
class LiveState:
    """The file as the storage has it now, to compare with the latest recorded version."""

    etag: str
    content_tag: str
    size: int
    web_url: str = ""


@dataclass(frozen=True)
class RemoteVersion:
    """A version as the storage itself keeps it."""

    id: str
    size: int
    last_modified: str = ""


def changed_since(version, live: LiveState | None) -> bool:
    """
    Whether the file in the storage differs from `version` (a ``DocumentVersion``): by content tag when both have one
    (it changes only with the content), else by eTag (which also changes when only the name or other metadata does).
    """
    if live is None:
        return False
    if version.content_tag and live.content_tag:
        return version.content_tag != live.content_tag
    return bool(version.etag) and version.etag != live.etag


class DocumentStore(ABC):
    """
    A place that keeps the bytes of documents. ``document`` and ``version`` arguments are ``Document`` and
    ``DocumentVersion`` instances (only their fields are read; no query is made).
    """

    provider: str = ""

    @abstractmethod
    def max_file_size(self) -> int:
        """The largest file, in bytes, this store accepts."""

    @abstractmethod
    def begin_upload(self, request: UploadRequest) -> PlannedUpload:
        """Prepare a place for the bytes and say where the browser sends them."""

    @abstractmethod
    def finish_upload(self, state: dict, *, size: int) -> StoredFile:
        """
        Check that the bytes arrived (and are `size` bytes long) and read back what the storage says about them.
        Raises UploadIncompleteError when they did not.
        """

    @abstractmethod
    def download_url(self, document, version, *, disposition: str = "attachment") -> str:
        """A short-lived, pre-authenticated address of the bytes of exactly this version."""

    @abstractmethod
    def thumbnail_url(self, document) -> str | None:
        """A short-lived address of a picture of the current file, or None when the store has none."""

    @abstractmethod
    def list_versions(self, document, versions=()) -> list[RemoteVersion]:
        """
        The versions the storage keeps of the document, newest first. `versions` are the recorded
        ``DocumentVersion`` rows, for a store that keeps nothing beyond them (native).
        """

    @abstractmethod
    def live_state(self, document) -> LiveState | None:
        """The file as it is now in the storage; None when it cannot be changed outside Pi-Plane (native)."""

    @abstractmethod
    def open_stream(self, document, version) -> Iterator[bytes]:
        """The bytes of exactly this version, chunk by chunk (the checksum check reads them; a proxy would)."""

    def current_file(self, document) -> StoredFile:
        """
        The file as it is now, as a version to record: what adopting a change made outside Pi-Plane records. Only a
        store whose files can change outside Pi-Plane has this.
        """
        raise DocumentStoreError(
            "This document cannot be changed outside Pi-Plane, so there is nothing to adopt.",
            code="nothing_to_adopt",
            http_status=409,
        )
