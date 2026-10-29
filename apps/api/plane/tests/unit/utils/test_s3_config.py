# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The S3 client configuration must not make uploads carry checksums.

botocore sends a CRC32 checksum with every upload by default. Google Cloud Storage's S3-compatible API rejects such
an upload (``SignatureDoesNotMatch``), which made every export fail on a bucket there.
"""

import io

import boto3
import pytest
from botocore.awsrequest import AWSResponse

from plane.utils.s3_config import s3_client_config


class _EmptyBody:
    def stream(self, *args, **kwargs):
        return iter(())


def _client():
    return boto3.client(
        "s3",
        endpoint_url="https://storage.example.test",
        aws_access_key_id="key",
        aws_secret_access_key="secret",
        region_name="auto",
        config=s3_client_config(),
    )


@pytest.mark.unit
class TestS3ClientConfig:
    def test_signature_version_and_checksum_policy(self):
        config = s3_client_config()
        assert config.signature_version == "s3v4"
        assert config.request_checksum_calculation == "when_required"
        assert config.response_checksum_validation == "when_required"

    def test_an_upload_carries_no_checksum_header(self):
        sent = []

        def capture(request, **kwargs):
            sent.append({key.lower(): value for key, value in request.headers.items()})
            return AWSResponse(request.url, 200, {}, _EmptyBody())

        client = _client()
        client.meta.events.register("before-send.s3.PutObject", capture)
        client.upload_fileobj(
            io.BytesIO(b"zip" * 100), "bucket", "key.zip", ExtraArgs={"ContentType": "application/zip"}
        )

        assert sent, "the upload was not sent"
        assert not [
            name for name in sent[0] if name.startswith("x-amz-checksum") or name == "x-amz-sdk-checksum-algorithm"
        ]
        assert "x-amz-trailer" not in sent[0]
