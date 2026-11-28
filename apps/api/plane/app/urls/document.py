# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    DocumentAdoptEndpoint,
    DocumentEndpoint,
    DocumentLibraryDefaultEndpoint,
    DocumentLibraryEndpoint,
    DocumentLibrarySiteEndpoint,
    DocumentThumbnailEndpoint,
    DocumentUploadEndpoint,
    DocumentUploadFinishEndpoint,
    DocumentVersionDownloadEndpoint,
    DocumentVersionEndpoint,
    ProjectDocumentFolderEndpoint,
    ProjectDocumentSettingsEndpoint,
)

DOCUMENTS = "workspaces/<str:slug>/projects/<uuid:project_id>/documents"
LIBRARIES = "workspaces/<str:slug>/document-libraries"
PROJECT_SETTINGS = "workspaces/<str:slug>/projects/<uuid:project_id>/document-settings"

urlpatterns = [
    path(f"{DOCUMENTS}/", DocumentEndpoint.as_view(), name="project-documents"),
    path(f"{DOCUMENTS}/uploads/", DocumentUploadEndpoint.as_view(), name="project-document-upload"),
    path(
        f"{DOCUMENTS}/uploads/finish/",
        DocumentUploadFinishEndpoint.as_view(),
        name="project-document-upload-finish",
    ),
    path(f"{DOCUMENTS}/<uuid:document_id>/", DocumentEndpoint.as_view(), name="project-document"),
    path(
        f"{DOCUMENTS}/<uuid:document_id>/versions/",
        DocumentVersionEndpoint.as_view(),
        name="project-document-versions",
    ),
    path(
        f"{DOCUMENTS}/<uuid:document_id>/versions/<int:number>/",
        DocumentVersionEndpoint.as_view(),
        name="project-document-version",
    ),
    path(
        f"{DOCUMENTS}/<uuid:document_id>/versions/<int:number>/download/",
        DocumentVersionDownloadEndpoint.as_view(),
        name="project-document-version-download",
    ),
    path(
        f"{DOCUMENTS}/<uuid:document_id>/thumbnail/",
        DocumentThumbnailEndpoint.as_view(),
        name="project-document-thumbnail",
    ),
    path(
        f"{DOCUMENTS}/<uuid:document_id>/adopt/",
        DocumentAdoptEndpoint.as_view(),
        name="project-document-adopt",
    ),
    # Document libraries of the workspace and the project's choice (B4, docs/document-libraries.md)
    path(f"{LIBRARIES}/", DocumentLibraryEndpoint.as_view(), name="document-libraries"),
    path(f"{LIBRARIES}/sites/", DocumentLibrarySiteEndpoint.as_view(), name="document-library-sites"),
    path(f"{LIBRARIES}/default/", DocumentLibraryDefaultEndpoint.as_view(), name="document-library-default"),
    path(f"{LIBRARIES}/<uuid:library_id>/", DocumentLibraryEndpoint.as_view(), name="document-library"),
    path(f"{PROJECT_SETTINGS}/", ProjectDocumentSettingsEndpoint.as_view(), name="project-document-settings"),
    path(
        f"{PROJECT_SETTINGS}/folder/",
        ProjectDocumentFolderEndpoint.as_view(),
        name="project-document-folder",
    ),
]
