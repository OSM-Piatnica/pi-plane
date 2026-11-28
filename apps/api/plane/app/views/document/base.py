# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Documents of a project: uploading (begin, finish), listing, versions, download and thumbnail redirects, and
adopting a change made directly in SharePoint. See ``docs/document-store.md``.

Who may do what: every member of the project reads (a guest of a project with "guests see everything" off only the
documents of the work items they created, and those of the project itself, as ``FileAsset.is_project_accessible_to``
rules); admins and members upload and adopt, within the work item edit rule.
"""

# Django imports
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.document import DocumentSerializer, DocumentVersionSerializer
from plane.db.models import (
    ChecksumStatus,
    Document,
    DocumentVersion,
    Issue,
    Project,
    ProjectMember,
    WorkspaceMember,
)
from plane.utils.document_store.base import DocumentStoreError
from plane.utils.document_store.service import (
    DocumentRequestError,
    adopt_external_change,
    begin_upload,
    external_change,
    finish_upload,
    store_for_document,
)
from plane.utils.work_item_edit_rule import work_item_edit_denied

GUEST_DENIED = "You are not allowed to view this document."


def _error(message, code, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message, "error_code": code}, status=http_status)


def _store_error(error: DocumentStoreError | DocumentRequestError):
    return _error(error.message, error.code, error.http_status)


def _is_restricted_guest(request, slug, project_id) -> bool:
    """A guest of a project whose guests see only their own work items (and not an admin of the workspace)."""
    restricted = ProjectMember.objects.filter(
        workspace__slug=slug,
        project_id=project_id,
        member=request.user,
        role=ROLE.GUEST.value,
        is_active=True,
        project__guest_view_all_features=False,
    ).exists()
    if not restricted:
        return False
    return not WorkspaceMember.objects.filter(
        workspace__slug=slug, member=request.user, role=ROLE.ADMIN.value, is_active=True
    ).exists()


def _documents(request, slug, project_id):
    """The documents of the project the caller may see, with their versions prefetched newest first."""
    queryset = Document.objects.filter(workspace__slug=slug, project_id=project_id).prefetch_related(
        Prefetch(
            "versions",
            queryset=DocumentVersion.objects.order_by("-number"),
            to_attr="recorded_versions",
        )
    )
    if _is_restricted_guest(request, slug, project_id):
        # Issue.objects, as issue detail uses, so the guest's own archived and draft items still count
        own = Issue.objects.filter(project_id=project_id, created_by=request.user).values("id")
        queryset = queryset.filter(Q(issue__isnull=True) | Q(issue_id__in=own))
    return queryset


def _document(request, slug, project_id, document_id):
    """(document, error response): the document when the caller may see it."""
    document = _documents(request, slug, project_id).filter(pk=document_id).first()
    if document is None:
        exists = Document.objects.filter(workspace__slug=slug, project_id=project_id, pk=document_id).exists()
        if exists:
            return None, _error(GUEST_DENIED, "forbidden", status.HTTP_403_FORBIDDEN)
        return None, _error("Document not found.", "not_found", status.HTTP_404_NOT_FOUND)
    return document, None


def _version(document, number):
    return next((version for version in document.recorded_versions if version.number == number), None)


class DocumentEndpoint(BaseAPIView):
    """
    GET without an ID lists the documents of the project (``?issue_id=`` narrows to one work item), newest first.
    GET with an ID answers one document with all its versions and ``changed_externally``: True when the file was
    changed in SharePoint since its latest version, None when SharePoint could not be asked, False otherwise.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, document_id=None):
        if document_id is None:
            queryset = _documents(request, slug, project_id)
            issue_id = request.query_params.get("issue_id")
            if issue_id:
                queryset = queryset.filter(issue_id=issue_id)
            return Response(DocumentSerializer(queryset.order_by("-created_at"), many=True).data)

        document, error = _document(request, slug, project_id, document_id)
        if error:
            return error
        data = DocumentSerializer(document).data
        data["versions"] = DocumentVersionSerializer(document.recorded_versions, many=True).data
        latest = document.recorded_versions[0] if document.recorded_versions else None
        data["changed_externally"] = external_change(document, latest)
        return Response(data)


class DocumentUploadEndpoint(BaseAPIView):
    """
    POST begins an upload: ``{"name", "type", "size", "issue_id"?}`` for a new document, ``{"document_id",
    "type", "size", "replace_external_change"?}`` for a new version. Answers ``{"upload_id", "upload_token",
    "upload": {"kind", "url", "method", "fields", "headers", "expires_at", "chunk_size"?, "chunk_multiple"?},
    "provider"}``: the browser sends the bytes as ``upload`` says, then finishes the upload with the token.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        project = get_object_or_404(Project, workspace__slug=slug, pk=project_id)
        data = request.data if isinstance(request.data, dict) else {}
        document = issue = None
        if data.get("document_id"):
            document = Document.objects.filter(project=project, pk=data["document_id"]).first()
            if document is None:
                return _error("Document not found.", "not_found", status.HTTP_404_NOT_FOUND)
            issue_id = document.issue_id
        else:
            issue_id = data.get("issue_id")
            if issue_id:
                issue = Issue.issue_objects.filter(project=project, pk=issue_id).first()
                if issue is None:
                    return _error("Work item not found.", "not_found", status.HTTP_404_NOT_FOUND)
        if issue_id:
            denied = work_item_edit_denied(request.user, project_id, [issue_id])
            if denied is not None:
                return denied
        try:
            answer = begin_upload(
                project=project,
                user=request.user,
                name=document.name if document is not None else data.get("name"),
                mime_type=data.get("type"),
                size=data.get("size"),
                issue=issue,
                document=document,
                replace_external_change=data.get("replace_external_change") is True,
                request=request,
            )
        except (DocumentRequestError, DocumentStoreError) as error:
            return _store_error(error)
        return Response(answer, status=status.HTTP_200_OK)


class DocumentUploadFinishEndpoint(BaseAPIView):
    """
    POST ``{"upload_token", "sha256"}`` after the bytes were sent: records the version (and the document, for a
    first upload) and answers the document with ``version``. Finishing the same upload again answers the same.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        project = get_object_or_404(Project, workspace__slug=slug, pk=project_id)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            version = finish_upload(
                project=project,
                user=request.user,
                token=data.get("upload_token"),
                sha256=data.get("sha256"),
                request=request,
            )
        except (DocumentRequestError, DocumentStoreError) as error:
            return _store_error(error)
        data = DocumentSerializer(version.document).data
        data["version"] = DocumentVersionSerializer(version).data
        return Response(data, status=status.HTTP_200_OK)


class DocumentVersionEndpoint(BaseAPIView):
    """GET lists the versions of a document, newest first, or one version by its number."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, document_id, number=None):
        document, error = _document(request, slug, project_id, document_id)
        if error:
            return error
        if number is None:
            return Response(DocumentVersionSerializer(document.recorded_versions, many=True).data)
        version = _version(document, number)
        if version is None:
            return _error("Version not found.", "not_found", status.HTTP_404_NOT_FOUND)
        return Response(DocumentVersionSerializer(version).data)


class DocumentVersionDownloadEndpoint(BaseAPIView):
    """
    GET redirects to a short-lived address of exactly this version. ``?disposition=inline`` asks for inline
    (honoured by the native store for the types that are safe inline). A version whose checksum does not match is
    refused with ``checksum_mismatch`` unless ``?accept_mismatch=true``: it is never served silently.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, document_id, number):
        document, error = _document(request, slug, project_id, document_id)
        if error:
            return error
        version = _version(document, number)
        if version is None:
            return _error("Version not found.", "not_found", status.HTTP_404_NOT_FOUND)
        if version.checksum_status == ChecksumStatus.MISMATCH and request.query_params.get("accept_mismatch") != "true":
            return _error(
                "The stored file of this version does not match what was uploaded.",
                "checksum_mismatch",
                status.HTTP_409_CONFLICT,
            )
        disposition = "inline" if request.query_params.get("disposition") == "inline" else "attachment"
        try:
            url = store_for_document(document, request=request).download_url(document, version, disposition=disposition)
        except DocumentStoreError as error:
            return _store_error(error)
        return HttpResponseRedirect(url)


class DocumentThumbnailEndpoint(BaseAPIView):
    """GET redirects to a picture of the current file; 404 ``no_thumbnail`` when the store has none (native)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, document_id):
        document, error = _document(request, slug, project_id, document_id)
        if error:
            return error
        try:
            url = store_for_document(document, request=request).thumbnail_url(document)
        except DocumentStoreError as error:
            return _store_error(error)
        if not url:
            return _error("There is no thumbnail of this document.", "no_thumbnail", status.HTTP_404_NOT_FOUND)
        return HttpResponseRedirect(url)


class DocumentAdoptEndpoint(BaseAPIView):
    """POST records the file as it now is in SharePoint as a new version (it was changed there directly)."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, document_id):
        document, error = _document(request, slug, project_id, document_id)
        if error:
            return error
        if document.issue_id:
            denied = work_item_edit_denied(request.user, project_id, [document.issue_id])
            if denied is not None:
                return denied
        try:
            version = adopt_external_change(document, user=request.user)
        except (DocumentRequestError, DocumentStoreError) as error:
            return _store_error(error)
        data = DocumentSerializer(Document.objects.get(pk=document.pk)).data
        data["version"] = DocumentVersionSerializer(version).data
        return Response(data, status=status.HTTP_200_OK)


__all__ = [
    "DocumentAdoptEndpoint",
    "DocumentEndpoint",
    "DocumentThumbnailEndpoint",
    "DocumentUploadEndpoint",
    "DocumentUploadFinishEndpoint",
    "DocumentVersionDownloadEndpoint",
    "DocumentVersionEndpoint",
]
