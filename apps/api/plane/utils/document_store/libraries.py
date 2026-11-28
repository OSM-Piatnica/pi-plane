# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Where new documents of a project go: the workspace's default library, a project's own choice of library and folder
(``ProjectDocumentSettings``), or Pi-Plane's own storage. See ``docs/document-libraries.md``.

Folder paths are kept "/"-separated, without leading or trailing "/"; "" is the root of the library. Every part must
be a name SharePoint accepts as it is (``sharepoint_file_name`` would leave it unchanged), so what the administrator
types is exactly the folder that is used.
"""

from dataclasses import dataclass
from urllib.parse import quote

from plane.db.models.document import DocumentLibrary, DocumentProvider, ProjectDocumentSettings, ProjectDocumentStore

from .sharepoint import sharepoint_file_name

MAX_FOLDER_LENGTH = 400
MAX_FOLDER_SEGMENTS = 20


class FolderPathError(ValueError):
    """A folder path that cannot be used; the message is safe to show."""


def normalize_folder_path(value) -> str:
    """
    `value` as a folder path ("A/B/C"), or FolderPathError. Leading, trailing and doubled "/" (and "\\") are
    dropped, and each part is trimmed.
    """
    text = str(value or "").replace("\\", "/")
    segments = [segment.strip() for segment in text.split("/") if segment.strip()]
    if len(segments) > MAX_FOLDER_SEGMENTS:
        raise FolderPathError(f"A folder may be at most {MAX_FOLDER_SEGMENTS} levels deep.")
    for segment in segments:
        if segment in (".", "..") or sharepoint_file_name(segment, fallback="") != segment:
            raise FolderPathError(
                f'"{segment}" cannot be a folder name in SharePoint. Leave out " * : < > ? \\ | # % and do not '
                "end a name with a dot."
            )
    path = "/".join(segments)
    if len(path) > MAX_FOLDER_LENGTH:
        raise FolderPathError(f"A folder path may be at most {MAX_FOLDER_LENGTH} characters long.")
    return path


def folder_segments(path) -> tuple[str, ...]:
    return tuple(segment for segment in str(path or "").split("/") if segment)


def folder_web_url(library_web_url: str, segments) -> str:
    """
    The SharePoint address of a folder of a library: the library's address with the folder's parts appended, each
    encoded. Built, not asked for, so it is only a guess when the folder does not exist yet (**unverified** until
    B1 that SharePoint opens a folder by this address; the folder endpoint asks Graph when it can).
    """
    base = str(library_web_url or "").rstrip("/")
    if not base:
        return ""
    return "/".join([base, *(quote(segment, safe="") for segment in segments)])


def default_library(workspace_id):
    """The SharePoint library new documents of the workspace go to, or None."""
    return DocumentLibrary.objects.filter(
        workspace_id=workspace_id, is_default=True, provider=DocumentProvider.SHAREPOINT
    ).first()


def project_settings(project):
    return ProjectDocumentSettings.objects.filter(project=project).select_related("library").first()


@dataclass(frozen=True)
class ProjectTarget:
    """Where a new document of a project goes."""

    provider: str
    # The SharePoint library, or None for Pi-Plane's own storage
    library: DocumentLibrary | None
    # The project's folder under the library's root folder
    project_folder: tuple[str, ...]
    # Why it is Pi-Plane's own storage: "chosen" (the project says so), "no_library" (no default library and no
    # library chosen), "sharepoint_off" (SharePoint is not usable on the instance); "" for SharePoint
    native_reason: str = ""

    @property
    def folder(self) -> tuple[str, ...]:
        """The project's folder from the root of the library."""
        if self.library is None:
            return ()
        return (*folder_segments(self.library.root_path), *self.project_folder)

    def item_folder(self, project_identifier: str, sequence_id: int | None) -> tuple[str, ...]:
        """The folder of a new document under the library's root: the project's folder, then ``PROJECT-12``."""
        if sequence_id is None:
            return self.project_folder
        return (*self.project_folder, sharepoint_file_name(f"{project_identifier}-{sequence_id}", fallback="item"))


_LOOK_UP = object()


def project_target(project, *, sharepoint_enabled: bool | None = None, settings=_LOOK_UP) -> ProjectTarget:
    """
    Where a new document of `project` goes. A library chosen by the project wins over the workspace default; a
    removed library counts as not chosen. Without a usable SharePoint every document goes to Pi-Plane's storage.
    `settings` is the project's ``ProjectDocumentSettings`` (None: it has none); left out, it is looked up.
    """
    if sharepoint_enabled is None:
        from plane.utils.sharepoint.config import is_sharepoint_enabled

        sharepoint_enabled = is_sharepoint_enabled()
    if settings is _LOOK_UP:
        settings = project_settings(project)
    store = settings.store if settings is not None else ProjectDocumentStore.WORKSPACE
    custom_folder = folder_segments(settings.folder) if settings is not None else ()
    project_folder = custom_folder or (sharepoint_file_name(project.identifier, fallback="project"),)

    if store == ProjectDocumentStore.NATIVE:
        return ProjectTarget(DocumentProvider.NATIVE, None, (), native_reason="chosen")
    library = None
    if store == ProjectDocumentStore.SHAREPOINT and settings.library is not None:
        if settings.library.deleted_at is None:
            library = settings.library
    if library is None:
        library = default_library(project.workspace_id)
    if library is None:
        return ProjectTarget(DocumentProvider.NATIVE, None, (), native_reason="no_library")
    if not sharepoint_enabled:
        return ProjectTarget(DocumentProvider.NATIVE, None, (), native_reason="sharepoint_off")
    return ProjectTarget(DocumentProvider.SHAREPOINT, library, project_folder)
