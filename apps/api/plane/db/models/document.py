# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Documents with immutable, numbered versions, kept either in Pi-Plane's own object storage ("native") or in a
SharePoint document library. See ``docs/document-store.md`` and ``plane.utils.document_store``.

These are not ``FileAsset`` rows: a file asset is one object in Pi-Plane's own bucket, while a document is one
logical file with a history, possibly living in a library Pi-Plane does not own.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from .base import BaseModel
from .project import ProjectBaseModel


class DocumentProvider(models.TextChoices):
    """Where the bytes of a document live."""

    NATIVE = "native", "Pi-Plane storage"
    SHAREPOINT = "sharepoint", "SharePoint"


class ChecksumStatus(models.TextChoices):
    """
    Whether the stored bytes of a version are the bytes that were uploaded.

    ``pending`` until the background check has read the stored version; ``verified`` when its SHA-256 equals the one
    the browser computed (or, for a version adopted from SharePoint, once the check has recorded it); ``mismatch``
    when they differ. A mismatching version is never served without the caller acknowledging it.
    """

    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    MISMATCH = "mismatch", "Mismatch"


class DocumentVersionSource(models.TextChoices):
    """How a version came to be recorded."""

    # Uploaded through Pi-Plane
    UPLOAD = "upload", "Upload"
    # The file was changed directly in SharePoint, and someone adopted that change as a new version
    ADOPTED = "adopted", "Adopted"


class DocumentLibrary(BaseModel):
    """
    A SharePoint document library a workspace keeps its documents in.

    Workspace admins add these in the workspace settings ("Document libraries"; see ``docs/document-libraries.md``).
    New documents of a workspace go to its default library when SharePoint is switched on, under
    ``{root_path}/{PROJECT}/{PROJECT}-{sequence}/``, unless the project overrides it (``ProjectDocumentSettings``).
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="document_libraries")
    name = models.CharField(max_length=255, blank=True, default="")
    provider = models.CharField(max_length=20, choices=DocumentProvider.choices, default=DocumentProvider.SHAREPOINT)
    site_id = models.CharField(max_length=255)
    drive_id = models.CharField(max_length=255)
    # Folder inside the library, "/"-separated, without leading or trailing "/"; "" is the root of the library
    root_path = models.CharField(max_length=400, blank=True, default="")
    web_url = models.URLField(max_length=2000, blank=True, default="")
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Document Library"
        verbose_name_plural = "Document Libraries"
        db_table = "document_libraries"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(is_default=True, deleted_at__isnull=True),
                name="document_library_one_default_per_workspace",
            ),
            models.UniqueConstraint(
                fields=["workspace", "drive_id", "root_path"],
                condition=Q(deleted_at__isnull=True),
                name="document_library_unique_folder_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.name or self.drive_id} ({self.workspace_id})"


class Document(ProjectBaseModel):
    """
    One logical file of a project, optionally of a work item, with its versions.

    For SharePoint, the document is one file in the library (``external_drive_id`` and ``external_item_id``), and
    every upload through Pi-Plane makes a new SharePoint version of it. The drive is copied here so that a document
    stays reachable when its library is later removed from the workspace settings.
    """

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255)
    provider = models.CharField(max_length=20, choices=DocumentProvider.choices)
    library = models.ForeignKey(
        DocumentLibrary, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    external_drive_id = models.CharField(max_length=255, blank=True, default="")
    external_item_id = models.CharField(max_length=255, blank=True, default="")
    web_url = models.URLField(max_length=2000, blank=True, default="")

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        db_table = "documents"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["project", "issue"], name="document_project_issue_idx"),
        ]

    def __str__(self):
        return self.name


class DocumentVersion(ProjectBaseModel):
    """
    One immutable version of a document, numbered 1, 2, ... per document.

    People never change or remove a row; only the checksum check writes ``checksum_status``, ``sha256`` (for an
    adopted version) and ``checksum_checked_at``. For the native store ``storage_key`` names the object (one object
    per version); for SharePoint ``external_version_id`` names the SharePoint version of the document's file.
    ``etag`` and ``content_tag`` are what the store said about the file when the version was recorded; comparing
    them with the live values tells whether the file was changed outside Pi-Plane.
    """

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=255)
    size = models.BigIntegerField()
    storage_key = models.CharField(max_length=800, blank=True, default="")
    external_version_id = models.CharField(max_length=255, blank=True, default="")
    etag = models.CharField(max_length=255, blank=True, default="")
    content_tag = models.CharField(max_length=255, blank=True, default="")
    # Hex SHA-256 of the bytes: computed by the browser for an upload, by the checksum check for an adopted version
    sha256 = models.CharField(max_length=64, blank=True, default="")
    checksum_status = models.CharField(max_length=20, choices=ChecksumStatus.choices, default=ChecksumStatus.PENDING)
    checksum_checked_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=20, choices=DocumentVersionSource.choices, default=DocumentVersionSource.UPLOAD
    )
    # The upload this version finished; makes finishing the same upload twice return the same version
    upload_id = models.UUIDField(null=True, blank=True, unique=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="document_versions"
    )
    uploaded_at = models.DateTimeField()

    class Meta:
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"
        db_table = "document_versions"
        ordering = ("document", "-number")
        constraints = [
            # Numbers are never reused, not even after a soft delete
            models.UniqueConstraint(fields=["document", "number"], name="document_version_unique_number"),
        ]

    def __str__(self):
        return f"{self.document_id} v{self.number}"


class ProjectDocumentStore(models.TextChoices):
    """Where new documents of a project go."""

    # Whatever the workspace says: its default library, or Pi-Plane's own storage when it has none
    WORKSPACE = "workspace", "Workspace default"
    NATIVE = "native", "Pi-Plane storage"
    SHAREPOINT = "sharepoint", "SharePoint library"


class ProjectDocumentSettings(ProjectBaseModel):
    """
    A project's override of where its new documents go: another library of the workspace (or Pi-Plane's own
    storage) and another folder. Without a row the workspace default applies. Existing documents never move.

    ``folder`` is the project's folder under the library's root folder ("/"-separated, without leading or trailing
    "/"), in place of the project identifier; "" keeps the identifier. Documents of a work item still go to a
    ``{PROJECT}-{sequence}`` folder inside it.
    """

    store = models.CharField(
        max_length=20, choices=ProjectDocumentStore.choices, default=ProjectDocumentStore.WORKSPACE
    )
    # Only with store "sharepoint"; when the library is removed the project falls back to the workspace default
    library = models.ForeignKey(
        DocumentLibrary, on_delete=models.SET_NULL, null=True, blank=True, related_name="project_settings"
    )
    folder = models.CharField(max_length=400, blank=True, default="")

    class Meta:
        verbose_name = "Project Document Settings"
        verbose_name_plural = "Project Document Settings"
        db_table = "project_document_settings"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(deleted_at__isnull=True),
                name="project_document_settings_unique_project_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.project_id}: {self.store}"
