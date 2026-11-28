# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The checksum check of a document version: read the stored bytes, compute their SHA-256 and compare it with the one
the browser computed during the upload. A version adopted from SharePoint has no such value; the check records the
one it computes.

A storage that cannot be read now (throttling, a network error) leaves the version ``pending`` and the task tries
again later; a version that is gone from the storage stays ``pending`` and is logged.
"""

import hashlib
import logging

from celery import shared_task
from django.utils import timezone

from plane.db.models.document import ChecksumStatus, DocumentVersion
from plane.utils.document_store.base import DocumentStoreError, FileMissingError
from plane.utils.document_store.service import store_for_document
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane.worker")

RETRY_DELAYS = (60, 300, 1800)


def compute_sha256(chunks) -> tuple[str, int]:
    """(hex SHA-256, number of bytes) of an iterable of byte chunks."""
    digest = hashlib.sha256()
    total = 0
    for chunk in chunks:
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def check_version(version, store=None) -> str:
    """Read and compare one version; store and return its new checksum status. Raises DocumentStoreError."""
    document = version.document
    # No deadline: a large file may take minutes to read
    store = store or store_for_document(document, client_options={"deadline": None})
    computed, size = compute_sha256(store.open_stream(document, version))
    fields = {"checksum_checked_at": timezone.now()}
    if not version.sha256:
        # Adopted from SharePoint: nothing to compare with, so this becomes the reference
        fields["sha256"] = computed
        status = ChecksumStatus.VERIFIED
    elif computed == version.sha256 and size == version.size:
        status = ChecksumStatus.VERIFIED
    else:
        status = ChecksumStatus.MISMATCH
        logger.warning("Document version %s: the stored bytes do not match its checksum", version.id)
    fields["checksum_status"] = status
    # Only these columns: the rest of a version never changes
    DocumentVersion.all_objects.filter(pk=version.pk).update(**fields)
    return status


@shared_task(bind=True, max_retries=len(RETRY_DELAYS))
def verify_document_version_checksum(self, version_id):
    version = DocumentVersion.objects.select_related("document").filter(pk=version_id).first()
    if version is None:
        return None
    try:
        return check_version(version)
    except FileMissingError as error:
        logger.warning("Document version %s: the stored file is missing (%s)", version_id, error.code)
        return None
    except DocumentStoreError as error:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=RETRY_DELAYS[self.request.retries]) from None
        logger.warning("Document version %s: the checksum check gave up (%s)", version_id, error.code)
        return None
    except Exception as error:
        log_exception(error)
        return None
