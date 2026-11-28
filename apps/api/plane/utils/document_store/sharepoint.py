# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The SharePoint document store: one file in a SharePoint document library per document, one SharePoint version per
Pi-Plane version, through the app-only Graph client of ``plane.utils.sharepoint``.

**Unverified until B1.** Everything here follows Microsoft's documentation and is tested against a fake Graph only.
In particular, nobody has yet confirmed on a real tenant that:

- the browser may ``PUT`` to an upload session URL and fetch a download URL from the Pi-Plane origin (CORS);
  this store assumes it may (the plan's default) and hands both addresses to the browser;
- an upload session by path makes the missing folders, and ``conflictBehavior: fail`` refuses an existing name
  when the session is created;
- the list of versions starts with the current version, and the content of the current version can be fetched by
  its version ID as well as by the item;
- ``cTag`` changes with the content only, and ``eTag`` with any change.

Layout: a new document of a work item goes to ``{root}/{PROJECT}/{PROJECT}-{sequence}/{name}``, a document of the
project to ``{root}/{PROJECT}/{name}`` (``default_folder``). A new version replaces the content of the same file.
"""

import logging
import re
import unicodedata
from contextlib import contextmanager

from plane.db.models.document import DocumentProvider
from plane.utils.sharepoint.client import MAX_ITEM_NAME_LENGTH
from plane.utils.sharepoint.errors import (
    SharePointConfigurationError,
    SharePointError,
    SharePointNotFoundError,
    SharePointResponseError,
    SharePointThrottledError,
)

from .base import (
    DocumentStore,
    DocumentStoreError,
    FileMissingError,
    FileTooLargeError,
    LiveState,
    NameTakenError,
    PlannedUpload,
    RemoteVersion,
    StoredFile,
    StoreNotConfiguredError,
    UploadIncompleteError,
    UploadRequest,
    UploadTarget,
    changed_since,
)

logger = logging.getLogger("plane.external")

# Graph wants every range but the last to be a multiple of 320 KiB, and at most 60 MiB; 10 MiB is what it suggests
UPLOAD_CHUNK_MULTIPLE = 320 * 1024
UPLOAD_CHUNK_SIZE = 32 * UPLOAD_CHUNK_MULTIPLE

_UNSAFE_NAME_CHARACTERS = re.compile(r'["*:<>?/\\|#%\x00-\x1f\x7f]')
# Names SharePoint keeps for itself, and prefixes of files it treats specially
_RESERVED_NAMES = {
    ".lock",
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{n}" for n in range(10)),
    *(f"lpt{n}" for n in range(10)),
    "desktop.ini",
}
_RESERVED_PREFIXES = ("~$", "_vti_")
# Room left for SharePoint's own "name 1.pdf" and for the folders in front of the name (whole path ≤ 400)
MAX_NAME_LENGTH = min(MAX_ITEM_NAME_LENGTH, 200)


def sharepoint_file_name(name, *, fallback: str = "document") -> str:
    """A file or folder name SharePoint accepts, as close to `name` as possible."""
    text = unicodedata.normalize("NFC", str(name or ""))
    text = _UNSAFE_NAME_CHARACTERS.sub("_", text).strip().rstrip(". ").strip()
    for prefix in _RESERVED_PREFIXES:
        if text.lower().startswith(prefix):
            text = "_" + text[len(prefix) :]
    stem, dot, extension = text.rpartition(".")
    if text.lower() in _RESERVED_NAMES or (dot and stem.lower() in _RESERVED_NAMES):
        text = f"_{text}"
    if len(text) > MAX_NAME_LENGTH:
        stem, dot, extension = text.rpartition(".")
        if dot and 0 < len(extension) <= 16:
            text = stem[: MAX_NAME_LENGTH - len(extension) - 1].rstrip(". ") + "." + extension
        else:
            text = text[:MAX_NAME_LENGTH].rstrip(". ")
    return text or fallback


def default_folder(project_identifier: str, sequence_id: int | None = None) -> tuple[str, ...]:
    """The folder of a new document under the library's root: ``PROJECT/PROJECT-12`` or ``PROJECT``."""
    project = sharepoint_file_name(project_identifier, fallback="project")
    if sequence_id is None:
        return (project,)
    return (project, sharepoint_file_name(f"{project_identifier}-{sequence_id}", fallback="item"))


def _translate(error: SharePointError) -> DocumentStoreError:
    """A SharePoint error as a store error; the message of the client is already written for people."""
    if isinstance(error, SharePointConfigurationError):
        return StoreNotConfiguredError(error.message, detail=error.detail)
    if isinstance(error, SharePointNotFoundError):
        return FileMissingError("SharePoint does not have this file (any more).", detail=error.detail)
    if isinstance(error, SharePointThrottledError):
        return DocumentStoreError(error.message, code="throttled", http_status=503, detail=error.detail)
    if isinstance(error, SharePointResponseError) and error.status == 409:
        return NameTakenError("A file of this name is already in the SharePoint folder.", detail=error.detail)
    return DocumentStoreError(error.message, code=f"sharepoint_{error.code}", detail=error.detail)


class SharePointStore(DocumentStore):
    """
    `library` (a ``DocumentLibrary``) is needed only for new documents: their drive and root folder. Existing
    documents carry their drive and item. `client_factory` makes a ``SharePointClient`` (tests pass one with a fake
    transport); `client_options` go to it (the checksum check passes ``deadline=None``).
    """

    provider = DocumentProvider.SHAREPOINT

    def __init__(self, *, library=None, client_factory=None, client_options=None, max_file_size: int | None = None):
        self.library = library
        self._client_factory = client_factory
        self._client_options = dict(client_options or {})
        self._max_file_size = max_file_size

    @contextmanager
    def _client(self):
        try:
            if self._client_factory is not None:
                client = self._client_factory(**self._client_options)
            else:
                from plane.utils.sharepoint.config import get_sharepoint_client

                client = get_sharepoint_client(**self._client_options)
            with client:
                yield client
        except SharePointError as error:
            logger.warning("SharePoint document store: %s (%s)", error.code, error.detail)
            raise _translate(error) from None

    def max_file_size(self) -> int:
        if self._max_file_size is not None:
            return self._max_file_size
        from plane.utils.sharepoint.config import get_sharepoint_max_file_size

        return get_sharepoint_max_file_size()

    # ------------------------------------------------------------------ uploads

    def _new_file_path(self, request: UploadRequest) -> tuple[str, str]:
        if self.library is None:
            raise StoreNotConfiguredError("No SharePoint library is set for this workspace.")
        root = [segment for segment in str(self.library.root_path or "").split("/") if segment]
        name = sharepoint_file_name(request.name)
        return "/".join([*root, *request.folder, name]), name

    def begin_upload(self, request: UploadRequest) -> PlannedUpload:
        if request.size > self.max_file_size():
            raise FileTooLargeError("The file is larger than SharePoint documents may be on this instance.")
        with self._client() as client:
            if request.item_id:
                session = client.create_upload_session_for_item(request.drive_id, request.item_id)
                state = {
                    "drive_id": request.drive_id,
                    "item_id": request.item_id,
                    "base_content_tag": request.base_content_tag,
                }
            else:
                path, name = self._new_file_path(request)
                drive_id = self.library.drive_id
                session = client.create_upload_session_for_path(drive_id, path)
                state = {"drive_id": drive_id, "path": path, "name": name}
        target = UploadTarget(
            kind="upload_session",
            url=session.upload_url,
            method="PUT",
            expires_at=session.expires_at,
            chunk_size=UPLOAD_CHUNK_SIZE,
            chunk_multiple=UPLOAD_CHUNK_MULTIPLE,
        )
        return PlannedUpload(target=target, state=state)

    def finish_upload(self, state: dict, *, size: int) -> StoredFile:
        drive_id = str(state.get("drive_id") or "")
        item_id = str(state.get("item_id") or "")
        path = str(state.get("path") or "")
        if not drive_id or not (item_id or path):
            raise UploadIncompleteError("This upload cannot be finished.")
        try:
            with self._client() as client:
                item = client.get_item(drive_id, item_id) if item_id else client.get_item_by_path(drive_id, path)
                base = str(state.get("base_content_tag") or "")
                if item_id and base and item.content_tag == base:
                    raise UploadIncompleteError("The new content has not arrived in SharePoint yet.")
                if item.size != size:
                    raise UploadIncompleteError(
                        "The file in SharePoint is not the size that was announced.",
                        code="size_mismatch",
                        detail=str(item.size),
                    )
                versions = client.list_versions(drive_id, item.id)
        except FileMissingError:
            raise UploadIncompleteError("The file has not arrived in SharePoint yet.") from None
        if not versions:
            raise UploadIncompleteError("SharePoint shows no version of the file yet.")
        return StoredFile(
            name=item.name,
            size=item.size,
            etag=item.etag,
            content_tag=item.content_tag,
            external_drive_id=item.drive_id or drive_id,
            external_item_id=item.id,
            external_version_id=versions[0].id,
            web_url=item.web_url,
        )

    # ------------------------------------------------------------------ reading

    @staticmethod
    def _download_url(client, document, version) -> str:
        item = client.get_item(document.external_drive_id, document.external_item_id, with_download_url=True)
        if item.download_url and not changed_since(version, _live(item)):
            # The file is still exactly this version
            return item.download_url
        if not version.external_version_id:
            raise FileMissingError("SharePoint has no record of this version.")
        return client.get_version_download_url(
            document.external_drive_id, document.external_item_id, version.external_version_id
        )

    def download_url(self, document, version, *, disposition: str = "attachment") -> str:
        # SharePoint decides the disposition of its download URLs; inline viewing goes through the viewer (C2)
        with self._client() as client:
            return self._download_url(client, document, version)

    def thumbnail_url(self, document) -> str | None:
        with self._client() as client:
            return client.get_thumbnail_url(document.external_drive_id, document.external_item_id)

    def list_versions(self, document, versions=()) -> list[RemoteVersion]:
        with self._client() as client:
            remote = client.list_versions(document.external_drive_id, document.external_item_id)
        return [RemoteVersion(id=entry.id, size=entry.size, last_modified=entry.last_modified) for entry in remote]

    def live_state(self, document) -> LiveState:
        with self._client() as client:
            return _live(client.get_item(document.external_drive_id, document.external_item_id))

    def current_file(self, document) -> StoredFile:
        """The file as it is now, as a version to record: what adopting a change made in SharePoint records."""
        with self._client() as client:
            item = client.get_item(document.external_drive_id, document.external_item_id)
            versions = client.list_versions(document.external_drive_id, item.id)
        if not versions:
            raise FileMissingError("SharePoint shows no version of the file.")
        return StoredFile(
            name=item.name,
            size=item.size,
            etag=item.etag,
            content_tag=item.content_tag,
            external_drive_id=document.external_drive_id,
            external_item_id=item.id,
            external_version_id=versions[0].id,
            web_url=item.web_url,
        )

    def open_stream(self, document, version):
        with self._client() as client:
            yield from client.iter_download(self._download_url(client, document, version))


def _live(item) -> LiveState:
    return LiveState(etag=item.etag, content_tag=item.content_tag, size=item.size, web_url=item.web_url)
