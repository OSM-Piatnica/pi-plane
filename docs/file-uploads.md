<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# File uploads and the storage

## What is kept in the storage

The storage (the bucket behind `AWS_S3_ENDPOINT_URL`: the bundled MinIO-compatible service by default, or any S3 service you point it at; or an Azure Blob Storage container, see [Azure Blob Storage](azure-blob-storage.md)) holds files only:

- work item attachments, and images pasted into work item descriptions, drafts and comments;
- images and files inserted into Pages;
- user avatars and profile covers, workspace logos and project covers;
- export files (each is a download link valid for 7 days; expired ones are deleted);
- the copies of cover and description images that duplicating a project makes.

Text is not there. The words of a Page, work item or comment are in the PostgreSQL database, as are the settings. An imported spreadsheet is read and imported within the request and is not stored; only a row in the export history records that the import ran (file name, options, result).

## The largest upload

One limit applies to every kind of upload above. It starts at `FILE_SIZE_LIMIT` (bytes, 5 MiB by default) and the instance administrator can change it without restarting anything: **God mode → General → File uploads**.

- It applies to new uploads. **Lowering it never touches files that are already stored**, however large they are.
- It can be set from 1 MB up to `FILE_SIZE_LIMIT_MAX` (100 MiB by default), which is also the largest request body the bundled proxy accepts. Raise `FILE_SIZE_LIMIT_MAX` in `plane.env` (Docker), `app.fileSizeLimitMax` (Helm) or with `-e` (all-in-one) to allow more, and keep it at least as large as `FILE_SIZE_LIMIT`. If you run another proxy or ingress in front, it has to allow the same size.
- "Use the default" next to a field removes that setting, and the `FILE_SIZE_LIMIT` of the environment applies again.
- People see the limit in the upload messages of the web app. They pick up a new value when they reload the page.
- An object store can have limits of its own. An S3-compatible store enforces the size announced for each upload itself; Azure Blob Storage cannot, so there a file over the announced size is deleted right after it is uploaded.

## Spreadsheet imports

Importing work items from a spreadsheet has two limits of its own, on the same page (**File uploads and imports**):

- **Largest spreadsheet** (15 MB by default, up to `FILE_SIZE_LIMIT_MAX`): the CSV, Excel or JSON file the person picks. It travels as an ordinary request, so it cannot be larger than the proxy accepts.
- **Most work items in one import** (500 by default, up to 5000). An import runs within a single request, so a very large one can run into the time limit of your web server or proxy.

Both apply to new imports at once, and the import page of the web app shows the file limit that is set.
