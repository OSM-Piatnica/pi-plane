# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Documents and versions in the database, on top of a store.

An upload has two steps. ``begin_upload`` asks the store for a place and returns, next to the target for the
browser, a signed upload token that holds everything the second step needs (nothing is written to the database
yet, so an abandoned upload leaves no row behind). ``finish_upload`` checks the token, asks the store whether the
bytes arrived, and records the version (and, for the first version, the document) under a lock on the document, so
numbers are consecutive. Finishing the same upload again returns the same version.

The SHA-256 the browser computed is stored with the version, and ``verify_document_version_checksum`` (a Celery
task) reads the stored bytes and compares.
"""

import re
from uuid import uuid4

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from plane.db.models.document import (
    ChecksumStatus,
    Document,
    DocumentLibrary,
    DocumentProvider,
    DocumentVersion,
    DocumentVersionSource,
)

from .base import DocumentStoreError, UploadRequest, changed_since
from .native import NativeStore
from .sharepoint import SharePointStore, default_folder

UPLOAD_TOKEN_SALT = "plane.documents.upload"
# How long the browser has between beginning and finishing an upload. Longer than a presigned POST lives (one hour
# by default), because a large file in a SharePoint upload session can take longer.
UPLOAD_TOKEN_MAX_AGE = 24 * 3600
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
MAX_NAME_LENGTH = 255


class DocumentRequestError(Exception):
    """A request about documents that cannot be done as asked; the message is safe to show."""

    def __init__(self, message: str, *, code: str, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


# ---------------------------------------------------------------------- choosing the store


def default_library(workspace_id):
    """The SharePoint library new documents of the workspace go to, or None."""
    return DocumentLibrary.objects.filter(
        workspace_id=workspace_id, is_default=True, provider=DocumentProvider.SHAREPOINT
    ).first()


def store_for_new_document(workspace_id, *, request=None):
    """
    (store, library) for a new document: SharePoint when it is switched on for the instance and the workspace has a
    default library, Pi-Plane's own storage otherwise. B4 adds the per-project override.
    """
    from plane.utils.sharepoint.config import is_sharepoint_enabled

    library = default_library(workspace_id)
    if library is not None and is_sharepoint_enabled():
        return SharePointStore(library=library), library
    return NativeStore(request=request), None


def store_for_document(document, *, request=None, client_options=None):
    """The store that keeps an existing document; SharePoint raises ``not_configured`` when it is switched off."""
    if document.provider == DocumentProvider.SHAREPOINT:
        return SharePointStore(library=document.library, client_options=client_options)
    return NativeStore(request=request)


# ---------------------------------------------------------------------- reading


def latest_version(document):
    return DocumentVersion.objects.filter(document=document).order_by("-number").first()


def external_change(document, version, store=None):
    """
    Whether the file was changed outside Pi-Plane since `version` (the latest one): True or False, or None when the
    store could not be asked (the answer is then unknown, not "no").
    """
    if version is None:
        return False
    try:
        store = store or store_for_document(document)
        return changed_since(version, store.live_state(document))
    except DocumentStoreError:
        return None


# ---------------------------------------------------------------------- uploading


def _clean_upload(name, mime_type, size):
    name = str(name or "").strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise DocumentRequestError("The file needs a name of at most 255 characters.", code="invalid_name")
    if not isinstance(mime_type, str) or mime_type not in settings.ATTACHMENT_MIME_TYPES:
        raise DocumentRequestError("This type of file cannot be uploaded.", code="invalid_type")
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        raise DocumentRequestError("The size of the file must be a whole number of bytes above 0.", code="invalid_size")
    return name, mime_type, size


def begin_upload(
    *,
    project,
    user,
    name,
    mime_type,
    size,
    issue=None,
    document=None,
    replace_external_change=False,
    request=None,
):
    """
    Prepare the upload of a new document (`document` None, optionally of `issue`) or of a new version of
    `document`. Returns ``{"upload_id", "upload_token", "upload", "provider"}``.

    A new version of a file that was changed outside Pi-Plane since its latest version is refused with
    ``changed_externally`` unless `replace_external_change`: the owner first decides whether to adopt that change.
    """
    name, mime_type, size = _clean_upload(name, mime_type, size)
    if document is not None:
        if mime_type != document.mime_type:
            raise DocumentRequestError(
                "A new version must be the same type of file as the document.", code="type_changed"
            )
        store = store_for_document(document, request=request)
        library = document.library
        latest = latest_version(document)
        live = store.live_state(document) if latest is not None else None
        if latest is not None and changed_since(latest, live) and not replace_external_change:
            raise DocumentRequestError(
                "The file was changed in SharePoint after its latest version. Adopt that change as a version, "
                "or confirm that the upload replaces it.",
                code="changed_externally",
                http_status=409,
            )
        base_tag = live.content_tag if live is not None else (latest.content_tag if latest else "")
        upload_request = UploadRequest(
            workspace_id=str(project.workspace_id),
            name=document.name,
            mime_type=mime_type,
            size=size,
            drive_id=document.external_drive_id,
            item_id=document.external_item_id,
            base_content_tag=base_tag,
        )
    else:
        store, library = store_for_new_document(project.workspace_id, request=request)
        upload_request = UploadRequest(
            workspace_id=str(project.workspace_id),
            name=name,
            mime_type=mime_type,
            size=size,
            folder=default_folder(project.identifier, issue.sequence_id if issue is not None else None),
        )

    planned = store.begin_upload(upload_request)
    upload_id = str(uuid4())
    token = signing.dumps(
        {
            "upload_id": upload_id,
            "workspace_id": str(project.workspace_id),
            "project_id": str(project.id),
            "user_id": str(user.id),
            "issue_id": str(issue.id) if issue is not None else None,
            "document_id": str(document.id) if document is not None else None,
            "name": name,
            "mime_type": mime_type,
            "size": size,
            "provider": store.provider,
            "library_id": str(library.id) if library is not None else None,
            "state": planned.state,
        },
        salt=UPLOAD_TOKEN_SALT,
        compress=True,
    )
    return {
        "upload_id": upload_id,
        "upload_token": token,
        "upload": planned.target.as_dict(),
        "provider": store.provider,
    }


def _read_token(token, *, project, user) -> dict:
    try:
        payload = signing.loads(str(token or ""), salt=UPLOAD_TOKEN_SALT, max_age=UPLOAD_TOKEN_MAX_AGE)
    except signing.SignatureExpired:
        raise DocumentRequestError("This upload has expired. Start it again.", code="upload_expired") from None
    except signing.BadSignature:
        raise DocumentRequestError("This is not a valid upload.", code="invalid_upload_token") from None
    if payload.get("project_id") != str(project.id) or payload.get("user_id") != str(user.id):
        raise DocumentRequestError("This is not a valid upload.", code="invalid_upload_token")
    return payload


def _next_number(document) -> int:
    # Soft-deleted versions keep their numbers: a number is never given twice
    highest = DocumentVersion.all_objects.filter(document=document).aggregate(highest=Max("number"))["highest"]
    return (highest or 0) + 1


def _record_version(document, stored, *, user, mime_type, sha256="", source, upload_id=None):
    return DocumentVersion.objects.create(
        document=document,
        project_id=document.project_id,
        workspace_id=document.workspace_id,
        number=_next_number(document),
        mime_type=mime_type,
        size=stored.size,
        storage_key=stored.storage_key,
        external_version_id=stored.external_version_id,
        etag=stored.etag,
        content_tag=stored.content_tag,
        sha256=sha256,
        checksum_status=ChecksumStatus.PENDING,
        source=source,
        upload_id=upload_id,
        uploaded_by=user,
        uploaded_at=timezone.now(),
    )


def _schedule_checksum(version):
    from plane.bgtasks.document_checksum_task import verify_document_version_checksum

    version_id = str(version.id)
    transaction.on_commit(lambda: verify_document_version_checksum.delay(version_id))


def finish_upload(*, project, user, token, sha256, request=None):
    """Record the version an upload made (and its document, for a first version). Returns the ``DocumentVersion``."""
    payload = _read_token(token, project=project, user=user)
    sha256 = str(sha256 or "").strip().lower()
    if not _SHA256_RE.fullmatch(sha256):
        raise DocumentRequestError(
            "The SHA-256 of the file is required, as 64 hexadecimal characters.", code="invalid_sha256"
        )
    existing = DocumentVersion.objects.filter(upload_id=payload["upload_id"]).select_related("document").first()
    if existing is not None:
        return existing

    document = None
    if payload.get("document_id"):
        document = Document.objects.filter(pk=payload["document_id"], project=project).first()
        if document is None:
            raise DocumentRequestError("The document no longer exists.", code="document_missing", http_status=404)
        store = store_for_document(document, request=request)
    elif payload["provider"] == DocumentProvider.SHAREPOINT:
        library = DocumentLibrary.objects.filter(pk=payload.get("library_id")).first()
        store = SharePointStore(library=library)
    else:
        store = NativeStore(request=request)

    stored = store.finish_upload(payload["state"], size=payload["size"])

    try:
        with transaction.atomic():
            if document is None:
                document = Document.objects.create(
                    project=project,
                    workspace_id=project.workspace_id,
                    issue_id=payload.get("issue_id"),
                    name=stored.name or payload["name"],
                    mime_type=payload["mime_type"],
                    provider=payload["provider"],
                    library_id=payload.get("library_id"),
                    external_drive_id=stored.external_drive_id,
                    external_item_id=stored.external_item_id,
                    web_url=stored.web_url,
                )
            else:
                # The lock makes concurrent uploads of one document take consecutive numbers
                document = Document.objects.select_for_update().get(pk=document.pk)
            version = _record_version(
                document,
                stored,
                user=user,
                mime_type=payload["mime_type"],
                sha256=sha256,
                source=DocumentVersionSource.UPLOAD,
                upload_id=payload["upload_id"],
            )
            _schedule_checksum(version)
    except IntegrityError:
        # The same upload finished at the same moment by another request
        existing = DocumentVersion.objects.filter(upload_id=payload["upload_id"]).first()
        if existing is None:
            raise
        return existing
    return version


def adopt_external_change(document, *, user):
    """
    Record the file as it now is in the storage as a new version (it was changed outside Pi-Plane). The checksum
    check then records its SHA-256. Refused with ``nothing_to_adopt`` when the file is still the latest version.
    """
    store = store_for_document(document)
    latest = latest_version(document)
    if latest is not None and not changed_since(latest, store.live_state(document)):
        raise DocumentRequestError(
            "The file has not changed since its latest version.", code="nothing_to_adopt", http_status=409
        )
    stored = store.current_file(document)
    with transaction.atomic():
        locked = Document.objects.select_for_update().get(pk=document.pk)
        version = _record_version(
            locked, stored, user=user, mime_type=document.mime_type, source=DocumentVersionSource.ADOPTED
        )
        _schedule_checksum(version)
    return version
