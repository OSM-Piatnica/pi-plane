# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Document libraries of a workspace (workspace settings, admins only) and a project's choice of library and folder
(project settings). See ``docs/document-libraries.md``.

A library is added by the address of its SharePoint site: the API looks the site up through Microsoft Graph, lists
its libraries, and stores the IDs of the one picked. Everything that talks to Graph is tested against a fake Graph
only (B1, the test on a real tenant, has not been done).
"""

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import Count, Q

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import (
    DocumentLibrary,
    DocumentProvider,
    Project,
    ProjectDocumentSettings,
    ProjectDocumentStore,
    ProjectMember,
    Workspace,
    WorkspaceMember,
)
from plane.license.api.views.sharepoint import SITE_ERRORS
from plane.utils.document_store.libraries import (
    FolderPathError,
    default_library,
    folder_segments,
    folder_web_url,
    normalize_folder_path,
    project_settings,
    project_target,
)
from plane.utils.sharepoint.client import parse_site_url
from plane.utils.sharepoint.config import get_sharepoint_client, is_sharepoint_enabled
from plane.utils.sharepoint.errors import (
    SharePointConfigurationError,
    SharePointError,
    SharePointNotFoundError,
)

MAX_LIBRARY_NAME_LENGTH = 255
NOT_CONFIGURED = (
    "SharePoint is not set up on this instance. An instance administrator sets it up and switches it on in "
    "God Mode, under Integrations → SharePoint."
)


def _error(message, code, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message, "error_code": code}, status=http_status)


def _sharepoint_error(error: SharePointError):
    """A failure of Graph as an answer; the site errors say what the administrator can do about them."""
    if isinstance(error, SharePointConfigurationError):
        return _error(NOT_CONFIGURED, "not_configured")
    code, message = SITE_ERRORS.get(type(error), (None, None))
    return _error(message or error.message, code or error.code)


def _library_data(library, *, counts=None):
    data = {
        "id": str(library.id),
        "name": library.name,
        "provider": library.provider,
        "site_id": library.site_id,
        "drive_id": library.drive_id,
        "root_path": library.root_path,
        "web_url": library.web_url,
        "folder_web_url": folder_web_url(library.web_url, folder_segments(library.root_path)),
        "is_default": library.is_default,
        "created_at": library.created_at,
    }
    if counts is not None:
        data.update(counts)
    return data


def _clean_name(value, fallback=""):
    name = str(value if value is not None else fallback).strip()
    if len(name) > MAX_LIBRARY_NAME_LENGTH:
        raise ValueError(f"A name may be at most {MAX_LIBRARY_NAME_LENGTH} characters long.")
    return name


def _set_default(workspace_id, library_id):
    """Make `library_id` the default library of the workspace, or none (Pi-Plane storage) when it is None."""
    with transaction.atomic():
        # The old default goes first: at most one default per workspace is a constraint
        DocumentLibrary.objects.filter(workspace_id=workspace_id, is_default=True).exclude(pk=library_id).update(
            is_default=False
        )
        if library_id is not None:
            DocumentLibrary.objects.filter(workspace_id=workspace_id, pk=library_id).update(is_default=True)


def _find_drive(site_url, drive_id):
    """(site, drive) from Graph: the site at `site_url` and its library `drive_id` (None when the site has none)."""
    with get_sharepoint_client() as client:
        site = client.get_site(site_url)
        drives = client.list_drives(site.id)
    return site, next((drive for drive in drives if drive.id == drive_id), None)


class DocumentLibrarySiteEndpoint(BaseAPIView):
    """POST ``{"site_url"}``: look the site up through Graph and list its document libraries."""

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        site_url = str(request.data.get("site_url") or "").strip()
        try:
            parse_site_url(site_url)
            with get_sharepoint_client() as client:
                site = client.get_site(site_url)
                drives = client.list_drives(site.id)
        except SharePointError as error:
            return _sharepoint_error(error)
        used = {
            (library.drive_id, library.root_path)
            for library in DocumentLibrary.objects.filter(workspace__slug=slug, site_id=site.id)
        }
        return Response(
            {
                "site": {"id": site.id, "name": site.name, "web_url": site.web_url},
                "drives": [
                    {
                        "id": drive.id,
                        "name": drive.name,
                        "web_url": drive.web_url,
                        "drive_type": drive.drive_type,
                        "used_root_paths": sorted(path for drive_id, path in used if drive_id == drive.id),
                    }
                    for drive in drives
                ],
            }
        )


class DocumentLibraryEndpoint(BaseAPIView):
    """
    GET lists the libraries of the workspace, with whether SharePoint is usable and which store new documents go
    to by default. POST ``{"site_url", "drive_id", "name"?, "root_path"?, "is_default"?}`` adds one; the site and
    the library are looked up again through Graph, so only what Graph confirms is stored. PATCH ``{"name"?,
    "root_path"?, "is_default"?}`` changes one; DELETE removes it (its documents stay where they are).
    """

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        libraries = DocumentLibrary.objects.filter(workspace__slug=slug).annotate(
            document_count=Count("documents", filter=Q(documents__deleted_at__isnull=True), distinct=True),
            project_count=Count(
                "project_settings",
                filter=Q(
                    project_settings__deleted_at__isnull=True,
                    project_settings__store=ProjectDocumentStore.SHAREPOINT,
                ),
                distinct=True,
            ),
        )
        sharepoint_enabled = is_sharepoint_enabled()
        has_default = any(library.is_default for library in libraries)
        return Response(
            {
                "sharepoint_enabled": sharepoint_enabled,
                # Where new documents go when a project does not choose
                "default_provider": (
                    DocumentProvider.SHAREPOINT if sharepoint_enabled and has_default else DocumentProvider.NATIVE
                ),
                "native": {"is_default": not has_default},
                "libraries": [
                    _library_data(
                        library,
                        counts={"document_count": library.document_count, "project_count": library.project_count},
                    )
                    for library in libraries.order_by("created_at")
                ],
            }
        )

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        site_url = str(request.data.get("site_url") or "").strip()
        drive_id = str(request.data.get("drive_id") or "").strip()
        if not drive_id:
            return _error("Pick a document library of the site.", "invalid_drive")
        try:
            root_path = normalize_folder_path(request.data.get("root_path"))
        except FolderPathError as error:
            return _error(str(error), "invalid_folder")
        try:
            parse_site_url(site_url)
            site, drive = _find_drive(site_url, drive_id)
        except SharePointError as error:
            return _sharepoint_error(error)
        if drive is None:
            return _error("The site has no document library with this ID.", "library_not_found")
        try:
            name = _clean_name(request.data.get("name"), fallback="") or drive.name
        except ValueError as error:
            return _error(str(error), "invalid_name")
        make_default = (
            bool(request.data.get("is_default")) or not DocumentLibrary.objects.filter(workspace=workspace).exists()
        )
        try:
            with transaction.atomic():
                library = DocumentLibrary.objects.create(
                    workspace=workspace,
                    name=name[:MAX_LIBRARY_NAME_LENGTH],
                    provider=DocumentProvider.SHAREPOINT,
                    site_id=site.id,
                    drive_id=drive.id,
                    root_path=root_path,
                    web_url=drive.web_url,
                )
                if make_default:
                    _set_default(workspace.id, library.id)
        except IntegrityError:
            return _error(
                "This folder of this library is already a library of the workspace.",
                "library_exists",
                status.HTTP_409_CONFLICT,
            )
        library.refresh_from_db()
        return Response(_library_data(library), status=status.HTTP_201_CREATED)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def patch(self, request, slug, library_id):
        library = DocumentLibrary.objects.filter(workspace__slug=slug, pk=library_id).first()
        if library is None:
            return _error("Library not found.", "not_found", status.HTTP_404_NOT_FOUND)
        fields = []
        if "name" in request.data:
            try:
                library.name = _clean_name(request.data.get("name"))
            except ValueError as error:
                return _error(str(error), "invalid_name")
            fields.append("name")
        if "root_path" in request.data:
            try:
                library.root_path = normalize_folder_path(request.data.get("root_path"))
            except FolderPathError as error:
                return _error(str(error), "invalid_folder")
            fields.append("root_path")
        try:
            with transaction.atomic():
                if fields:
                    library.save(update_fields=[*fields, "updated_at", "updated_by"])
                if "is_default" in request.data:
                    if request.data.get("is_default"):
                        _set_default(library.workspace_id, library.id)
                    elif library.is_default:
                        _set_default(library.workspace_id, None)
        except IntegrityError:
            return _error(
                "This folder of this library is already a library of the workspace.",
                "library_exists",
                status.HTTP_409_CONFLICT,
            )
        library.refresh_from_db()
        return Response(_library_data(library))

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def delete(self, request, slug, library_id):
        library = DocumentLibrary.objects.filter(workspace__slug=slug, pk=library_id).first()
        if library is None:
            return _error("Library not found.", "not_found", status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            # Projects that chose it go back to the workspace default at once (not only when the soft delete's
            # background job has run)
            ProjectDocumentSettings.objects.filter(library=library).update(
                library=None, store=ProjectDocumentStore.WORKSPACE
            )
            library.is_default = False
            library.save(update_fields=["is_default", "updated_at"])
            library.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentLibraryDefaultEndpoint(BaseAPIView):
    """POST ``{"library_id"}``: the default library of the workspace; ``null`` makes Pi-Plane storage the default."""

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        library_id = request.data.get("library_id")
        if library_id:
            if not DocumentLibrary.objects.filter(workspace=workspace, pk=library_id).exists():
                return _error("Library not found.", "not_found", status.HTTP_404_NOT_FOUND)
        else:
            library_id = None
        _set_default(workspace.id, library_id)
        return Response({"library_id": str(library_id) if library_id else None})


# ---------------------------------------------------------------------- projects


def _project_settings_data(project, settings, *, can_edit):
    sharepoint_enabled = is_sharepoint_enabled()
    target = project_target(project, sharepoint_enabled=sharepoint_enabled, settings=settings)
    workspace_default = default_library(project.workspace_id)
    libraries = DocumentLibrary.objects.filter(workspace_id=project.workspace_id).order_by("created_at")
    chosen = settings.library if settings is not None and settings.library is not None else None
    if chosen is not None and chosen.deleted_at is not None:
        chosen = None
    return {
        "store": settings.store if settings is not None else ProjectDocumentStore.WORKSPACE,
        "library_id": str(chosen.id) if chosen is not None else None,
        "folder": settings.folder if settings is not None else "",
        "default_folder": project.identifier,
        "sharepoint_enabled": sharepoint_enabled,
        "workspace_default": (
            {"id": str(workspace_default.id), "name": workspace_default.name} if workspace_default else None
        ),
        "libraries": [
            {
                "id": str(library.id),
                "name": library.name,
                "root_path": library.root_path,
                "web_url": library.web_url,
                "is_default": library.is_default,
            }
            for library in libraries
        ],
        "effective": {
            "provider": target.provider,
            "library": (
                {"id": str(target.library.id), "name": target.library.name} if target.library is not None else None
            ),
            "folder": "/".join(target.folder),
            "folder_web_url": (
                folder_web_url(target.library.web_url, target.folder) if target.library is not None else ""
            ),
            "native_reason": target.native_reason,
        },
        "can_edit": can_edit,
    }


def _is_project_admin(request, slug, project_id) -> bool:
    if ProjectMember.objects.filter(
        workspace__slug=slug, project_id=project_id, member=request.user, role=ROLE.ADMIN.value, is_active=True
    ).exists():
        return True
    return WorkspaceMember.objects.filter(
        workspace__slug=slug, member=request.user, role=ROLE.ADMIN.value, is_active=True
    ).exists()


class ProjectDocumentSettingsEndpoint(BaseAPIView):
    """
    GET answers where new documents of the project go: the project's choice (``store``: ``workspace``, ``native``
    or ``sharepoint`` with ``library_id``; ``folder``), the libraries it can choose from, and the ``effective``
    result. PUT ``{"store", "library_id"?, "folder"?}`` changes the choice (project admins). Existing documents do
    not move.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        project = Project.objects.get(workspace__slug=slug, pk=project_id)
        settings = project_settings(project)
        return Response(
            _project_settings_data(project, settings, can_edit=_is_project_admin(request, slug, project_id))
        )

    @allow_permission([ROLE.ADMIN])
    def put(self, request, slug, project_id):
        project = Project.objects.get(workspace__slug=slug, pk=project_id)
        store = str(request.data.get("store") or ProjectDocumentStore.WORKSPACE)
        if store not in ProjectDocumentStore.values:
            return _error("Choose the workspace default, a library or Pi-Plane storage.", "invalid_store")
        library = None
        if store == ProjectDocumentStore.SHAREPOINT:
            library = DocumentLibrary.objects.filter(
                workspace_id=project.workspace_id, pk=request.data.get("library_id") or None
            ).first()
            if library is None:
                return _error("Choose a library of this workspace.", "invalid_library")
        try:
            folder = normalize_folder_path(request.data.get("folder"))
        except FolderPathError as error:
            return _error(str(error), "invalid_folder")
        if store == ProjectDocumentStore.NATIVE:
            # A folder means nothing in Pi-Plane's own storage
            folder = ""

        settings = project_settings(project)
        if settings is None:
            settings = ProjectDocumentSettings(project=project, workspace_id=project.workspace_id)
        settings.store = store
        settings.library = library
        settings.folder = folder
        try:
            settings.save()
        except IntegrityError:
            # Saved at the same moment by another request: take that row
            settings = project_settings(project)
            settings.store, settings.library, settings.folder = store, library, folder
            settings.save()
        return Response(_project_settings_data(project, settings, can_edit=True))


class ProjectDocumentFolderEndpoint(BaseAPIView):
    """
    GET asks SharePoint for the project's folder: ``{"exists", "web_url"}``. The folder is made by the first
    upload, so until then ``exists`` is false and ``web_url`` is the address of the library's root folder.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        project = Project.objects.get(workspace__slug=slug, pk=project_id)
        target = project_target(project)
        if target.library is None:
            if target.native_reason == "sharepoint_off":
                return _error(NOT_CONFIGURED, "not_configured")
            return _error("New documents of this project are kept in Pi-Plane storage.", "not_sharepoint")
        library = target.library
        root_url = folder_web_url(library.web_url, folder_segments(library.root_path))
        try:
            with get_sharepoint_client() as client:
                item = client.get_item_by_path(library.drive_id, "/".join(target.folder))
        except SharePointNotFoundError:
            return Response({"exists": False, "web_url": root_url, "folder": "/".join(target.folder)})
        except SharePointError as error:
            return _sharepoint_error(error)
        if not item.is_folder:
            return _error("There is a file, not a folder, at the project's folder.", "not_a_folder")
        return Response({"exists": True, "web_url": item.web_url or root_url, "folder": "/".join(target.folder)})
