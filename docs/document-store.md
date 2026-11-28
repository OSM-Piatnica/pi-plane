# Document store

Pi-Plane keeps **documents**: files of a project or of a work item that have a history of numbered, immutable
versions. They are what acceptance (workstream C of the [roadmap](plans/workflow-roadmap.md)) reviews. A document
lives either in Pi-Plane's own object storage (the **native** store) or in a **SharePoint** document library.

> **Status (B3): API only, no screens yet.** The native store works on every installation. The SharePoint store is
> built against the SharePoint client of [SharePoint](sharepoint.md) and tested against a fake Microsoft Graph only.
> **The SharePoint path is unverified until B1**: nobody has yet tried it on a real tenant, and in particular nobody
> has checked that the browser may upload to and download from Microsoft directly (CORS). See
> [What B1 must confirm](#what-b1-must-confirm).

Documents are not attachments (`FileAsset`): an attachment is one object in Pi-Plane's bucket, a document is one
logical file with versions, possibly in a library Pi-Plane does not own.

## Where a new document goes

- **SharePoint** when SharePoint is switched on for the instance (`is_sharepoint_enabled`) and the workspace has a
  default document library. The file goes to `{root folder}/{PROJECT}/{PROJECT}-{number}/{name}` for a work item,
  `{root folder}/{PROJECT}/{name}` for the project itself. A file of that name that is already there is never
  overwritten: the upload is refused with `name_taken`.
- **Native** otherwise: one object per version under `{workspace id}/documents/` in the bucket (or Azure container)
  attachments use, with the same presigned uploads and downloads, so nothing new is needed from the storage.

A document stays in the store it was created in. A SharePoint document carries its drive and item IDs, so it stays
reachable when its library is later removed from the workspace settings. If SharePoint is switched off, its
documents answer `not_configured` until it is switched on again.

Choosing a library is B4 (workspace settings "Document libraries", and a per-project override). Until then a library
is a row of `DocumentLibrary` (`workspace`, `site_id`, `drive_id`, `root_path`, `web_url`, `is_default`) that an
instance administrator adds in the Django shell, after finding the IDs with "Test connection" in the admin app.

## Versions

- Numbered 1, 2, 3, ... per document. A number is never reused, not even after a version is removed by an
  administrator.
- People never change a version. The checksum check is the only writer after it is recorded.
- A new version must be the same type of file as the document (`type_changed` otherwise).
- In SharePoint a new version replaces the content of the same file, so SharePoint keeps its own version too. The
  SharePoint version ID is recorded with Pi-Plane's version, and a download always serves exactly that version.

### Checksums

The browser computes the SHA-256 of the file while uploading and sends it when it finishes the upload; it is
required. A background job (`verify_document_version_checksum`) then reads the stored bytes and compares:
`pending` → `verified` or `mismatch`. A version whose stored bytes no longer match is never served silently: its
download answers `checksum_mismatch` unless the caller passes `accept_mismatch=true`, so the interface can warn
first. If the storage cannot be read, the check is retried after 1, 5 and 30 minutes and then left `pending`.

### Changes made directly in SharePoint

SharePoint users can still edit the file in SharePoint. Pi-Plane compares the content tag (Graph's `cTag`, or the
`eTag` when there is none) of the file with that of the latest version:

- the detail of a document says `changed_externally: true` (or `null` when SharePoint could not be asked);
- uploading a new version is refused with `changed_externally` unless the request says
  `replace_external_change: true`;
- `adopt` records the file as it now is as a new version (`source: "adopted"`), whose SHA-256 the checksum check
  records.

A rename in SharePoint changes the `eTag` but not the content tag, and is not a change of content.

## API

All under `/api/workspaces/<slug>/projects/<project id>/documents/`.

| Method and path                       | What it does                                                                                    |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `GET /`                               | The documents of the project, newest first; `?issue_id=` for one work item.                     |
| `POST uploads/`                       | Begin an upload (see below).                                                                    |
| `POST uploads/finish/`                | `{"upload_token", "sha256"}`: record the version; answers the document with `version`.          |
| `GET <id>/`                           | One document with all its `versions` and `changed_externally`.                                  |
| `GET <id>/versions/`, `versions/<n>/` | The versions, newest first, or one by number.                                                   |
| `GET <id>/versions/<n>/download/`     | Redirect to a short-lived address of exactly that version; `?disposition=inline` (native only). |
| `GET <id>/thumbnail/`                 | Redirect to a picture of the current file (SharePoint); `404 no_thumbnail` for native.          |
| `POST <id>/adopt/`                    | Record the file as changed in SharePoint as a new version.                                      |

**Beginning an upload.** A new document: `{"name", "type", "size", "issue_id"?}`. A new version:
`{"document_id", "type", "size", "replace_external_change"?}`. The answer is
`{"upload_id", "upload_token", "provider", "upload": {...}}`, where `upload.kind` tells the browser what to do:

| `kind`           | Store          | What the browser does                                                                                                                            |
| ---------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `presigned_post` | native (S3)    | a form POST to `url` with `fields`, the file last, as for attachments                                                                            |
| `put`            | native (Azure) | one `PUT` of the file to `url` with `headers`                                                                                                    |
| `upload_session` | SharePoint     | `PUT` ranges of the file to `url` with `Content-Range`, each at most `chunk_size` and, except the last, a multiple of `chunk_multiple` (320 KiB) |
| `proxy`          | reserved       | not used yet; for the case that B1 finds the browser cannot reach Microsoft                                                                      |

Nothing is written to the database when an upload begins: the signed `upload_token` (valid 24 hours, only for the
same person and project) carries what finishing needs. Finishing the same upload twice answers the same version.

Errors answer `{"error": "<message>", "error_code": "<code>"}`. Codes: `invalid_name`, `invalid_type` (the types
attachments accept), `invalid_size`, `file_too_large` (`FILE_SIZE_LIMIT` for native, `SHAREPOINT_MAX_FILE_SIZE` for
SharePoint), `type_changed`, `changed_externally`, `name_taken`, `upload_incomplete`, `size_mismatch`,
`invalid_sha256`, `invalid_upload_token`, `upload_expired`, `document_missing`, `checksum_mismatch`, `no_thumbnail`,
`nothing_to_adopt`, `not_configured`, `file_missing`, `throttled`, and `sharepoint_<code>` for other errors of the
SharePoint client.

## Who may do what

- **Read** (list, detail, versions, download, thumbnail): admins, members and guests of the project. A guest of a
  project whose guests do not see all features sees the documents of the project itself and of the work items they
  created, the rule of attachments (`FileAsset.is_project_accessible_to`).
- **Upload and adopt**: admins and members, and only on work items the work item edit rule (`utils/work_item_edit_rule.py`, see [user groups](user-groups.md)) lets them
  change. Guests do not upload documents (unlike attachments).
- Access goes through Pi-Plane's permissions. SharePoint's own permissions are not applied to access through
  Pi-Plane (the app signs in as itself; see [SharePoint](sharepoint.md)).
- Nothing deletes a document or a version yet.

## What B1 must confirm

The SharePoint store follows Microsoft's documentation; each point below is assumed, not observed:

1. **CORS.** The browser may `PUT` to an upload session URL and `GET` a download URL from the Pi-Plane origin. If
   not, the store answers `begin_upload` with kind `proxy` and the API streams the bytes; the views and models do
   not change (`open_stream` already reads the bytes for the checksum check).
2. An upload session by path creates missing folders, and `conflictBehavior: fail` refuses an existing name when
   the session is created (`409`).
3. `GET .../versions` lists the current version first; `GET .../versions/{id}/content` redirects to the bytes of
   that version.
4. `cTag` changes only with content, `eTag` with any change.
5. Download, upload and thumbnail addresses are on `*.sharepoint.com` or `*.svc.ms` (others are refused).
6. Library settings: versioning must be on, and a retention or version-trimming policy that removes old versions
   makes their downloads answer `file_missing`.

## For developers

- Interface: `apps/api/plane/utils/document_store/base.py` (`DocumentStore`, `UploadTarget`, the errors).
- Stores: `native.py` (on `get_storage()`; `iter_object` was added to `S3Storage` and `AzureBlobStorage`) and
  `sharepoint.py` (on `SharePointClient`, whose file and version calls were added in B3).
- Recording: `service.py` (store choice, upload token, numbering under a row lock, adopting); checksum check:
  `apps/api/plane/bgtasks/document_checksum_task.py`.
- Models: `apps/api/plane/db/models/document.py` (`DocumentLibrary`, `Document`, `DocumentVersion`), migration
  `0166_documents`. Acceptance (C1) points `Approval.document` and `ApprovalVersion.document_version` at these.
- Views: `apps/api/plane/app/views/document/base.py`; URLs: `apps/api/plane/app/urls/document.py`.
- Tests: `apps/api/plane/tests/unit/utils/test_document_store_native.py`,
  `apps/api/plane/tests/unit/utils/test_document_store_sharepoint.py` (fake Graph),
  `apps/api/plane/tests/contract/app/test_documents_app.py` (endpoints on the native store).
