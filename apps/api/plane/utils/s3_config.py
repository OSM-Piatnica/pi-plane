# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The one botocore configuration every S3 client of the API uses."""

from botocore.config import Config


def s3_client_config() -> Config:
    """Signature V4, and checksums only where S3 requires them.

    Since botocore 1.36 every upload carries a checksum (a CRC32 trailer on a streamed body) by default. AWS S3
    and MinIO accept that; Google Cloud Storage's S3-compatible API and some other S3-compatible stores answer
    ``SignatureDoesNotMatch``. ``when_required`` sends no checksum unless an operation demands one, which every
    store accepts.
    """
    return Config(
        signature_version="s3v4",
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
