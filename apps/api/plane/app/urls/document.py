# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import (
    DocumentAdoptEndpoint,
    DocumentEndpoint,
    DocumentThumbnailEndpoint,
    DocumentUploadEndpoint,
    DocumentUploadFinishEndpoint,
    DocumentVersionDownloadEndpoint,
    DocumentVersionEndpoint,
)

DOCUMENTS = "workspaces/<str:slug>/projects/<uuid:project_id>/documents"

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
]
