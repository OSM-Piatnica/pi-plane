<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Azure Blob Storage

Pi-Plane can keep its files (attachments, images, avatars, covers, exports) in an Azure Blob Storage container instead of an S3-compatible bucket. Select it with `STORAGE_PROVIDER=azure`.

The API signs shared access signatures (SAS) with the storage account key, so browsers upload to and download from the container directly, as they do with presigned URLs on S3.

> **Status:** tested against the Azurite emulator, not against a real Azure storage account: uploads from the API and from the browser (with CORS), signed downloads, avatars, exports, copying, listing and deleting, the container being created at start, and the removal of a file larger than announced. Not tested: a real account, private endpoints, other clouds, and the Helm settings on a cluster. Try it on a test account first.

## Setting it up

1. Create a storage account and a **private** container (no anonymous access).
2. Copy an access key of the account (Security + networking → Access keys). The key gives full access to the account, so use an account of its own for Pi-Plane.
3. Allow browsers to reach the container: CORS rules for the **Blob service**, with your `WEB_URL` (and your Space URL, if it differs) as origin:

   ```bash
   az storage cors add --services b --account-name <account> \
     --origins https://plane.example.com --methods GET PUT HEAD OPTIONS \
     --allowed-headers "x-ms-*" "content-type" --exposed-headers "*" --max-age 3600
   ```

4. Set the Pi-Plane side:

   | Setting                                                      | Value                                                                                                                                                  |
   | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
   | `STORAGE_PROVIDER`                                           | `azure`                                                                                                                                                |
   | `USE_MINIO`                                                  | `0`                                                                                                                                                    |
   | `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY` | The account and its key; or `AZURE_STORAGE_CONNECTION_STRING` instead of both                                                                          |
   | `AZURE_STORAGE_CONTAINER`                                    | The container (`AWS_S3_BUCKET_NAME` is used when this is empty). It is created at start if it does not exist.                                          |
   | `AZURE_STORAGE_ENDPOINT`                                     | Optional. Defaults to `https://<account>.blob.core.windows.net`; set it for another cloud (for example `https://<account>.blob.core.chinacloudapi.cn`) |
   | `AZURE_STORAGE_PUBLIC_ENDPOINT`                              | Optional. What browsers should use when it is not the address the API uses (a private endpoint, an emulator)                                           |
   - **Docker Compose:** put them in `plane.env` and restart. `docker-compose.yaml` passes them to the API, worker and scheduler. The bundled `plane-minio` service can stay; it is unused.
   - **Helm:** `objectStorage.provider: azure`, `objectStorage.bundled.enabled: false`, `objectStorage.azure.accountName`, `objectStorage.bucket` (the container) and `objectStorage.azure.accountKeySecret` (a Secret you create with the key). The chart refuses an incomplete setup.
   - **All-in-one image:** not supported yet; it requires S3 settings.

Files already in another storage are not copied. Move them yourself (for example with `azcopy`).

## How it differs from S3

- **Upload size.** An S3 upload carries a policy that limits the size. A SAS cannot do that, so the size announced for an upload is checked right after the upload, and a file over it is deleted and the upload counts as failed. The limit itself is the same one as everywhere (see [file uploads](file-uploads.md)); until the check runs the oversized file exists in the container, and a signature is valid for an hour at most (`SIGNED_URL_EXPIRATION`).
- **Download links.** A link is a SAS with read access to one blob. As on S3, only a few image types are served inline; everything else downloads.
- **Exports** are written to the container with a link valid for 7 days; expired ones are deleted.
