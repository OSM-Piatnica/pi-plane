# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Azure Blob Storage, with the methods of ``plane.settings.storage.S3Storage``.

Selected with ``STORAGE_PROVIDER=azure``; see ``get_storage``. The API signs shared access signatures (SAS) with the
account key, so a browser uploads to and downloads from the container directly, as it does with presigned URLs on S3.

Two differences from S3 the callers must live with:

* An upload is a single ``PUT`` of the file (``generate_presigned_post`` answers with ``method`` and ``headers`` for
  the browser to send), not a multipart form.
* A SAS cannot limit the size of what is uploaded, as an S3 POST policy does. The size announced for an upload is
  checked once the file is there (see ``get_asset_object_metadata``), and a file over it is deleted.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
from django.conf import settings

from plane.utils.exception_logger import log_exception

# The browser sends this with every upload so the blob is stored as a block blob of the right type
BLOB_TYPE_HEADER = "x-ms-blob-type"
BLOB_CONTENT_TYPE_HEADER = "x-ms-blob-content-type"


class AzureBlobStorage:
    """Signs and performs the operations Pi-Plane needs on one container of an Azure storage account."""

    def __init__(self, request=None):
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            self.service = BlobServiceClient.from_connection_string(connection_string)
        else:
            account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
            if not account_name or not account_key:
                raise ValueError(
                    "Azure Blob Storage needs AZURE_STORAGE_CONNECTION_STRING, or AZURE_STORAGE_ACCOUNT_NAME "
                    "and AZURE_STORAGE_ACCOUNT_KEY."
                )
            endpoint = os.environ.get("AZURE_STORAGE_ENDPOINT") or f"https://{account_name}.blob.core.windows.net"
            self.service = BlobServiceClient(account_url=endpoint, credential=account_key)

        self.account_name = self.service.account_name
        self.account_key = self.service.credential.account_key
        self.container_name = os.environ.get("AZURE_STORAGE_CONTAINER") or os.environ.get("AWS_S3_BUCKET_NAME")
        if not self.container_name:
            raise ValueError("Azure Blob Storage needs AZURE_STORAGE_CONTAINER.")
        # What a browser can reach, when it is not the address the API uses (an emulator, a private endpoint)
        self.public_endpoint = (os.environ.get("AZURE_STORAGE_PUBLIC_ENDPOINT") or self.service.url).rstrip("/")
        self.signed_url_expiration = int(os.environ.get("SIGNED_URL_EXPIRATION", "3600"))
        self.container = self.service.get_container_client(self.container_name)

    # -- signing -----------------------------------------------------------------------------------------------

    def _sas(self, object_name, permission, expiration, **response_headers):
        now = datetime.now(timezone.utc)
        return generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=str(object_name),
            account_key=self.account_key,
            permission=permission,
            # A few minutes back, so a browser clock that runs slow does not find the signature not yet valid
            start=now - timedelta(minutes=5),
            expiry=now + timedelta(seconds=expiration),
            **response_headers,
        )

    def _blob_url(self, object_name, sas):
        return f"{self.public_endpoint}/{self.container_name}/{quote(str(object_name), safe='/')}?{sas}"

    def _get_content_disposition(self, disposition, filename=None):
        # Asset names are client-editable; use only a non-empty string, else a random name.
        if not isinstance(filename, str) or not filename:
            filename = uuid.uuid4().hex
        return f"{disposition}; filename*=UTF-8''{quote(filename)}"

    def generate_presigned_post(self, object_name, file_type, file_size, expiration=None):
        """What a browser needs to upload one file: a URL with write access, and the request to make.

        ``file_size`` cannot be enforced by a SAS; it is checked after the upload instead.
        """
        if expiration is None:
            expiration = self.signed_url_expiration
        sas = self._sas(object_name, BlobSasPermissions(create=True, write=True), expiration)
        return {
            "url": self._blob_url(object_name, sas),
            "fields": {},
            "method": "PUT",
            "headers": {
                BLOB_TYPE_HEADER: "BlockBlob",
                BLOB_CONTENT_TYPE_HEADER: file_type,
                "Content-Type": file_type,
            },
        }

    def generate_presigned_url(
        self,
        object_name,
        expiration=None,
        http_method="GET",
        disposition="inline",
        filename=None,
        content_type=None,
    ):
        """A URL with read access to one blob.

        As on S3, inline is honoured only for a content type in ``INLINE_SAFE_MIME_TYPES``, which is then pinned as the
        response type; anything else, including SVG and HTML, is served as an attachment.
        """
        if expiration is None:
            expiration = self.signed_url_expiration
        content_type = content_type.split(";")[0].strip().lower() if isinstance(content_type, str) else ""
        response_headers = {}
        if disposition == "inline" and content_type in settings.INLINE_SAFE_MIME_TYPES:
            response_headers["content_type"] = content_type
        else:
            disposition = "attachment"
        response_headers["content_disposition"] = self._get_content_disposition(disposition, filename)
        try:
            sas = self._sas(object_name, BlobSasPermissions(read=True), expiration, **response_headers)
        except (AzureError, ValueError) as error:
            log_exception(error)
            return None
        return self._blob_url(object_name, sas)

    # -- operations ----------------------------------------------------------------------------------------------

    def get_object_metadata(self, object_name):
        try:
            properties = self.container.get_blob_client(str(object_name)).get_blob_properties()
        except ResourceNotFoundError:
            # A missing object (upload never completed) is expected, not an error
            return None
        except AzureError as error:
            log_exception(error)
            return None
        return {
            "ContentType": properties.content_settings.content_type,
            "ContentLength": properties.size,
            "LastModified": properties.last_modified.isoformat() if properties.last_modified else None,
            "ETag": properties.etag,
            "Metadata": properties.metadata or {},
        }

    def copy_object(self, object_name, new_object_name):
        """Copy a blob inside the container. Returns something truthy on success, None on failure."""
        try:
            source_url = self._blob_url(
                object_name,
                self._sas(object_name, BlobSasPermissions(read=True), 300),
            )
            # The copy is read by the storage service, which can reach the container at its own address
            source_url = source_url.replace(self.public_endpoint, self.service.url.rstrip("/"), 1)
            target = self.container.get_blob_client(str(new_object_name))
            target.start_copy_from_url(source_url)
            for _ in range(60):
                status = target.get_blob_properties().copy.status
                if status == "success":
                    return {"CopyObjectResult": {"ETag": target.get_blob_properties().etag}}
                if status in ("failed", "aborted"):
                    return None
        except AzureError as error:
            log_exception(error)
            return None
        return None

    def upload_file(self, file_obj, object_name: str, content_type: str = None, extra_args: dict = None) -> bool:
        """Upload a file from the server."""
        try:
            self.container.upload_blob(
                name=str(object_name),
                data=file_obj,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type) if content_type else None,
            )
            return True
        except AzureError as error:
            log_exception(error)
            return False

    def delete_files(self, object_names):
        try:
            for object_name in object_names:
                try:
                    self.container.delete_blob(str(object_name))
                except ResourceNotFoundError:
                    pass
            return True
        except AzureError as error:
            log_exception(error)
            return False

    def ensure_container(self):
        """Create the container when it does not exist yet; returns whether it had to be created."""
        try:
            self.container.create_container()
            return True
        except ResourceExistsError:
            return False
