# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Documents and their versions, as the app reads them. Storage keys and external IDs stay on the server."""

from rest_framework import serializers

from plane.db.models import Document, DocumentVersion

from .base import BaseSerializer


class DocumentVersionSerializer(BaseSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "number",
            "mime_type",
            "size",
            "sha256",
            "checksum_status",
            "checksum_checked_at",
            "source",
            "uploaded_by",
            "uploaded_at",
        ]
        read_only_fields = fields


class DocumentSerializer(BaseSerializer):
    """``latest_version`` and ``version_count`` come from the view (annotation or prefetch), not from a query each."""

    latest_version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "workspace",
            "project",
            "issue",
            "name",
            "mime_type",
            "provider",
            "web_url",
            "created_by",
            "created_at",
            "latest_version",
            "version_count",
        ]
        read_only_fields = fields

    def _versions(self, document):
        # Prefetched by the view as ``recorded_versions``, newest first
        return getattr(document, "recorded_versions", None)

    def get_latest_version(self, document):
        versions = self._versions(document)
        if versions is None:
            versions = list(DocumentVersion.objects.filter(document=document).order_by("-number")[:1])
        return DocumentVersionSerializer(versions[0]).data if versions else None

    def get_version_count(self, document):
        versions = self._versions(document)
        if versions is None:
            return DocumentVersion.objects.filter(document=document).count()
        return len(versions)
