# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Azure Blob Storage as an object storage: the signed URLs, the choice of storage and the upload size check.

Nothing here talks to Azure: signing is done locally with the account key, and the SDK calls are replaced.
"""

from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import override_settings

from plane.settings.storage import S3Storage, get_storage
from plane.utils.azure_storage import AzureBlobStorage

# The well-known development account of the Azurite emulator
EMULATOR_KEY = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
EMULATOR_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    f"AccountKey={EMULATOR_KEY};BlobEndpoint=http://azurite:10000/devstoreaccount1;"
)


@pytest.fixture
def azure_env(monkeypatch):
    for name in (
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_ACCOUNT_KEY",
        "AZURE_STORAGE_ENDPOINT",
        "AZURE_STORAGE_PUBLIC_ENDPOINT",
        "AZURE_STORAGE_CONTAINER",
        "AWS_S3_BUCKET_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", EMULATOR_CONNECTION_STRING)
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "uploads")
    return monkeypatch


def query(url):
    return {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}


@pytest.mark.unit
class TestConfiguration:
    def test_a_connection_string_is_enough(self, azure_env):
        storage = AzureBlobStorage()
        assert storage.account_name == "devstoreaccount1"
        assert storage.container_name == "uploads"
        assert storage.public_endpoint == "http://azurite:10000/devstoreaccount1"

    def test_an_account_name_and_key_build_the_public_endpoint(self, azure_env):
        azure_env.delenv("AZURE_STORAGE_CONNECTION_STRING")
        azure_env.setenv("AZURE_STORAGE_ACCOUNT_NAME", "pilaneprod")
        azure_env.setenv("AZURE_STORAGE_ACCOUNT_KEY", EMULATOR_KEY)
        storage = AzureBlobStorage()
        assert storage.public_endpoint == "https://pilaneprod.blob.core.windows.net"

    def test_the_container_falls_back_to_the_bucket_name(self, azure_env):
        azure_env.delenv("AZURE_STORAGE_CONTAINER")
        azure_env.setenv("AWS_S3_BUCKET_NAME", "from-bucket")
        assert AzureBlobStorage().container_name == "from-bucket"

    def test_credentials_are_required(self, azure_env):
        azure_env.delenv("AZURE_STORAGE_CONNECTION_STRING")
        with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
            AzureBlobStorage()

    def test_a_container_is_required(self, azure_env):
        azure_env.delenv("AZURE_STORAGE_CONTAINER")
        with pytest.raises(ValueError, match="AZURE_STORAGE_CONTAINER"):
            AzureBlobStorage()

    def test_browsers_can_be_sent_to_another_address(self, azure_env):
        azure_env.setenv("AZURE_STORAGE_PUBLIC_ENDPOINT", "http://localhost:10000/devstoreaccount1/")
        post = AzureBlobStorage().generate_presigned_post("ws/a b.png", "image/png", 10)
        assert post["url"].startswith("http://localhost:10000/devstoreaccount1/uploads/ws/a%20b.png?")


@pytest.mark.unit
class TestUpload:
    def test_the_upload_is_one_put_with_write_access_only(self, azure_env):
        post = AzureBlobStorage().generate_presigned_post("ws/key.png", "image/png", 1000)
        assert post["method"] == "PUT"
        assert post["fields"] == {}
        assert post["headers"] == {
            "x-ms-blob-type": "BlockBlob",
            "x-ms-blob-content-type": "image/png",
            "Content-Type": "image/png",
        }
        parameters = query(post["url"])
        assert parameters["sp"] == "cw" and parameters["sr"] == "b" and parameters["sig"]
        assert post["url"].split("?")[0] == "http://azurite:10000/devstoreaccount1/uploads/ws/key.png"

    def test_the_signature_expires(self, azure_env):
        parameters = query(AzureBlobStorage().generate_presigned_post("k", "image/png", 1, expiration=600)["url"])
        assert parameters["st"] < parameters["se"]


@pytest.mark.unit
class TestDownload:
    def test_a_download_url_reads_one_blob_and_names_the_file(self, azure_env):
        url = AzureBlobStorage().generate_presigned_url(
            "ws/key.png", disposition="inline", filename="a b.png", content_type="image/png"
        )
        parameters = query(url)
        assert parameters["sp"] == "r"
        assert parameters["rsct"] == "image/png"
        assert parameters["rscd"] == "inline; filename*=UTF-8''a%20b.png"

    @pytest.mark.parametrize("content_type", ["image/svg+xml", "text/html", None, ""])
    def test_only_safe_types_are_served_inline(self, azure_env, content_type):
        parameters = query(
            AzureBlobStorage().generate_presigned_url(
                "k", disposition="inline", filename="f", content_type=content_type
            )
        )
        assert "rsct" not in parameters
        assert parameters["rscd"].startswith("attachment;")

    def test_an_attachment_is_asked_for_by_name(self, azure_env):
        parameters = query(AzureBlobStorage().generate_presigned_url("k", disposition="attachment", filename="f.zip"))
        assert parameters["rscd"] == "attachment; filename*=UTF-8''f.zip"


@pytest.mark.unit
class TestOperations:
    def test_copy_reads_the_source_at_the_address_of_the_service(self, azure_env):
        azure_env.setenv("AZURE_STORAGE_PUBLIC_ENDPOINT", "http://localhost:10000/devstoreaccount1")
        storage = AzureBlobStorage()
        target = mock.MagicMock()
        target.get_blob_properties.return_value.copy.status = "success"
        storage.container = mock.MagicMock()
        storage.container.get_blob_client.return_value = target

        assert storage.copy_object("ws/a.png", "ws/b.png")
        source_url = target.start_copy_from_url.call_args.args[0]
        assert source_url.startswith("http://azurite:10000/devstoreaccount1/uploads/ws/a.png?")

    def test_a_copy_that_fails_returns_none(self, azure_env):
        storage = AzureBlobStorage()
        target = mock.MagicMock()
        target.get_blob_properties.return_value.copy.status = "failed"
        storage.container = mock.MagicMock()
        storage.container.get_blob_client.return_value = target
        assert storage.copy_object("a", "b") is None

    def test_metadata_has_the_keys_s3_gives(self, azure_env):
        storage = AzureBlobStorage()
        properties = mock.MagicMock()
        properties.content_settings.content_type = "image/png"
        properties.size = 70
        properties.last_modified = None
        properties.etag = '"0x1"'
        properties.metadata = {}
        storage.container = mock.MagicMock()
        storage.container.get_blob_client.return_value.get_blob_properties.return_value = properties
        assert storage.get_object_metadata("k") == {
            "ContentType": "image/png",
            "ContentLength": 70,
            "LastModified": None,
            "ETag": '"0x1"',
            "Metadata": {},
        }

    def test_a_missing_blob_has_no_metadata(self, azure_env):
        from azure.core.exceptions import ResourceNotFoundError

        storage = AzureBlobStorage()
        storage.container = mock.MagicMock()
        storage.container.get_blob_client.return_value.get_blob_properties.side_effect = ResourceNotFoundError("gone")
        assert storage.get_object_metadata("k") is None

    def test_deleting_a_missing_blob_is_not_an_error(self, azure_env):
        from azure.core.exceptions import ResourceNotFoundError

        storage = AzureBlobStorage()
        storage.container = mock.MagicMock()
        storage.container.delete_blob.side_effect = ResourceNotFoundError("gone")
        assert storage.delete_files(["a", "b"]) is True


@pytest.mark.unit
class TestChoosingTheStorage:
    @override_settings(STORAGE_PROVIDER="s3")
    def test_s3_is_the_default(self):
        with mock.patch("plane.settings.storage.boto3"):
            assert isinstance(get_storage(), S3Storage)

    @override_settings(STORAGE_PROVIDER="azure")
    def test_azure_when_configured(self, azure_env):
        assert isinstance(get_storage(), AzureBlobStorage)


@pytest.mark.unit
@pytest.mark.django_db
class TestUploadSizeCheck:
    def asset(self, size, stored):
        from plane.db.models import FileAsset

        asset = mock.MagicMock(spec=FileAsset)
        asset.size = size
        asset.storage_metadata = {"ContentLength": stored}
        return asset

    def test_a_file_over_the_announced_size_is_over(self):
        from plane.bgtasks.storage_metadata_task import _exceeds_announced_size

        assert _exceeds_announced_size(self.asset(100, 101)) is True
        assert _exceeds_announced_size(self.asset(100, 100)) is False
        assert _exceeds_announced_size(self.asset(0, 5000)) is False
        assert _exceeds_announced_size(self.asset(100, None)) is False

    @override_settings(STORAGE_PROVIDER="azure")
    def test_the_task_removes_an_oversized_blob_on_azure(self):
        from plane.bgtasks.storage_metadata_task import get_asset_object_metadata
        from plane.db.models import FileAsset

        asset = mock.MagicMock(spec=FileAsset)
        asset.size = 100
        asset.asset.name = "ws/big.bin"
        storage = mock.MagicMock()
        storage.get_object_metadata.return_value = {"ContentLength": 5000}
        with (
            mock.patch("plane.bgtasks.storage_metadata_task.FileAsset.objects.get", return_value=asset),
            mock.patch("plane.bgtasks.storage_metadata_task.get_storage", return_value=storage),
        ):
            get_asset_object_metadata("id")
        storage.delete_files.assert_called_once_with(["ws/big.bin"])
        assert asset.is_uploaded is False and asset.is_deleted is True

    @override_settings(STORAGE_PROVIDER="s3")
    def test_s3_enforces_the_size_when_signing_so_nothing_is_removed_here(self):
        from plane.bgtasks.storage_metadata_task import get_asset_object_metadata
        from plane.db.models import FileAsset

        asset = mock.MagicMock(spec=FileAsset)
        asset.size = 100
        storage = mock.MagicMock()
        storage.get_object_metadata.return_value = {"ContentLength": 5000}
        with (
            mock.patch("plane.bgtasks.storage_metadata_task.FileAsset.objects.get", return_value=asset),
            mock.patch("plane.bgtasks.storage_metadata_task.get_storage", return_value=storage),
        ):
            get_asset_object_metadata("id")
        storage.delete_files.assert_not_called()
