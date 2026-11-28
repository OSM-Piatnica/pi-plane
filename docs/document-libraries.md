# Document libraries

Where the [documents](document-store.md) of a workspace are kept: in SharePoint document libraries or in Pi-Plane's
own storage. Workspace admins set up the libraries; a project can choose another library and folder for its new
documents.

> **Status (B4): not tried against a real tenant.** Everything that talks to Microsoft Graph (looking up a site,
> listing its libraries, checking a project's folder) is tested against a fake Graph only, like the rest of
> [SharePoint](sharepoint.md). B1, the test on a real tenant, has not been done.

## Workspace settings: Document libraries

Workspace settings → **Document libraries**, for workspace admins only.

- **Pi-Plane storage** is always in the list. It is the default while no SharePoint library is, and it is where
  documents go whenever SharePoint is not usable.
- **Add library**: paste the address of a SharePoint site (for example
  `https://contoso.sharepoint.com/sites/Projects`) and press **Look up**. Pi-Plane looks the site up through
  Microsoft Graph and lists its document libraries; pick one, give it a name (the library's own name by default)
  and a **root folder** inside it (for example `Pi-Plane/Projects`; empty is the root of the library). The site
  must already be granted to the Pi-Plane application (see [SharePoint](sharepoint.md), step 4).
- The first library added becomes the default. **Make default** moves the default to another library, or back to
  Pi-Plane storage.
- **Edit** changes the name and the root folder. New documents go to the new folder; documents already stored stay
  where they are.
- **Remove** takes the library off the list. Its documents stay in SharePoint and can still be opened (each document
  keeps the IDs of its drive and file). Projects that had chosen the library go back to the workspace default.
  Nothing is deleted in SharePoint.
- The same folder of the same library can be added only once. Adding a library looks the site up again, so only
  what Graph confirms is stored.

When SharePoint is not set up or switched off in God Mode, the page says so, **Add library** is disabled, and new
documents go to Pi-Plane storage even when a SharePoint library is the default.

## Project settings: Documents

Project settings → **Documents**, for project admins (and workspace admins).

- **New documents go to**: the workspace default, a library of the workspace, or Pi-Plane storage.
- **Project folder**: the project's folder under the library's root folder; empty means the project identifier.
  It may have several levels (`Klienci/ACME`). The documents of a work item go to a folder named after the work item
  inside it.
- The box at the top says where new documents go now and links to the folder: **Open folder in SharePoint** when
  it exists, or to the library's root folder while it does not (the folder is created with the first document).
- Changing the choice never moves documents that are already stored.

The resulting layout for a work item document is
`{library root folder}/{project folder or PROJECT}/{PROJECT}-{number}/{file name}`, and
`{library root folder}/{project folder or PROJECT}/{file name}` for a document of the project itself.

Folder names must be names SharePoint accepts as they are: no `" * : < > ? \ | # %`, no name ending in a dot, no
reserved names such as `con`. At most 20 levels and 400 characters.

## API

Workspace (admins of the workspace), under `/api/workspaces/<slug>/document-libraries/`:

| Method and path | What it does                                                                                                    |
| --------------- | --------------------------------------------------------------------------------------------------------------- |
| `GET /`         | `{"sharepoint_enabled", "default_provider", "native": {"is_default"}, "libraries": [...]}`, with counts.        |
| `POST sites/`   | `{"site_url"}`: the site and its libraries (`drives`, each with the root folders already added).                |
| `POST /`        | `{"site_url", "drive_id", "name"?, "root_path"?, "is_default"?}`: add a library; the first one becomes default. |
| `PATCH <id>/`   | `{"name"?, "root_path"?, "is_default"?}`.                                                                       |
| `DELETE <id>/`  | Remove; projects that chose it go back to the workspace default.                                                |
| `POST default/` | `{"library_id"}`; `null` makes Pi-Plane storage the default.                                                    |

Project, under `/api/workspaces/<slug>/projects/<project id>/document-settings/`:

| Method and path | Who             | What it does                                                                                                                  |
| --------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `GET /`         | admins, members | `{"store", "library_id", "folder", "libraries", "workspace_default", "effective": {...}, "can_edit", ...}`                    |
| `PUT /`         | admins          | `{"store": "workspace" \| "sharepoint" \| "native", "library_id"?, "folder"?}`                                                |
| `GET folder/`   | admins, members | Asks Graph for the project's folder: `{"exists", "web_url", "folder"}`; `web_url` is the root folder while it does not exist. |

Errors answer `{"error", "error_code"}`. Codes: `not_configured` (SharePoint not set up or switched off),
`invalid_site_url`, `site_access_denied`, `site_not_found`, `token_rejected`, `library_not_found`,
`library_exists`, `invalid_folder`, `invalid_name`, `invalid_store`, `invalid_library`, `not_sharepoint`,
`not_a_folder`, and the SharePoint client's codes (`throttled`, `timeout`, ...).

## For developers

- Model: `ProjectDocumentSettings` in `apps/api/plane/db/models/document.py`, migration
  `0167_project_document_settings` (one row per project; no row means the workspace default).
- Where a new document goes: `project_target` in `apps/api/plane/utils/document_store/libraries.py`, used by
  `store_for_new_document` in `service.py`; folder paths: `normalize_folder_path` (the web app mirrors it in
  `apps/web/helpers/document-library.ts`, the server decides).
- Views: `apps/api/plane/app/views/document/library.py`; URLs: `apps/api/plane/app/urls/document.py`.
- Web: `apps/web/components/workspace/document-libraries/`, `apps/web/components/project/settings/document-settings.tsx`,
  `apps/web/services/document-library.service.ts`.
- Tests: `apps/api/plane/tests/unit/utils/test_document_libraries.py`,
  `apps/api/plane/tests/contract/app/test_document_libraries_app.py` (fake Graph under the real client),
  `apps/web/tests/unit/document-library.test.ts`.
- **Unverified until B1**: that a folder opens in SharePoint by the address built from the library's address and
  the folder's path (used when Graph cannot be asked), and the answers Graph gives for a folder that does not exist.
