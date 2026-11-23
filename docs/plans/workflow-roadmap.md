# Pi-Plane roadmap: acceptance, Lite, RACI and scheduling, work item types, initiatives, navigation

Status: in progress; see the status table below. Written 2026-11-16 against `origin/preview` at `e53f08e243` (latest migration `0156`); brought up to date on 2026-11-23 (latest migration `0159`).
Audience: agents (and people) who will implement this one pull request at a time.

## 0. How to use this plan

- Each workstream (A to G) is split into pull requests with an ID such as `C3`. One agent takes one PR.
- Section 9 gives the order and what can run in parallel.
- Section 10 lists decisions that are still open. Each has a default, and the plan is written for the default. Do not wait for an answer unless the PR says "blocked on decision N".
- Facts about the code were mapped on 2026-11-16 and checked again on 2026-11-23. Check that a file, function or flag still exists before relying on it.

### Status

Updated by every roadmap PR (see "Keeping this plan current" below). Steps not listed have not started.

| Step   | State           | PRs                                                                                                                                                                                    | Notes                                                                                                                                          |
| ------ | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| A1     | merged          | [#473](https://github.com/OSM-Piatnica/pi-plane/pull/473)                                                                                                                              | `0158_issue_type_kind`; removing `is_epic` is [#512](https://github.com/OSM-Piatnica/pi-plane/issues/512)                                      |
| A2     | not started     |                                                                                                                                                                                        | a draft exists from before [#482](https://github.com/OSM-Piatnica/pi-plane/pull/482); check it against the A2 text below before reuse          |
| B2     | open            | [#479](https://github.com/OSM-Piatnica/pi-plane/pull/479)                                                                                                                              |                                                                                                                                                |
| D1     | merged, changed | [#476](https://github.com/OSM-Piatnica/pi-plane/pull/476)                                                                                                                              | departments are groups; no per-member field (see D1); one department per person is [#508](https://github.com/OSM-Piatnica/pi-plane/issues/508) |
| D2     | not started     |                                                                                                                                                                                        | an early draft assumed `WorkspaceMember.department`; redo it on department groups                                                              |
| D5     | merged          | [#475](https://github.com/OSM-Piatnica/pi-plane/pull/475), [#517](https://github.com/OSM-Piatnica/pi-plane/pull/517), [#519](https://github.com/OSM-Piatnica/pi-plane/pull/519) (open) | no cache, cap 2000; sorting by Float is [#518](https://github.com/OSM-Piatnica/pi-plane/issues/518)                                            |
| D6     | not started     |                                                                                                                                                                                        | a draft stacked on #475 exists; it must snapshot `finish_date` as well (see D6)                                                                |
| D8     | open            | [#478](https://github.com/OSM-Piatnica/pi-plane/pull/478)                                                                                                                              | `0160`; the deadline warning is left over (see D8)                                                                                             |
| F1     | merged          | [#472](https://github.com/OSM-Piatnica/pi-plane/pull/472), [#477](https://github.com/OSM-Piatnica/pi-plane/pull/477)                                                                   | `0159_initiatives`; `docs/initiatives.md`                                                                                                      |
| G1     | merged          | [#474](https://github.com/OSM-Piatnica/pi-plane/pull/474)                                                                                                                              | `docs/app-rail.md`                                                                                                                             |
| G2, G3 | open            | [#480](https://github.com/OSM-Piatnica/pi-plane/pull/480)                                                                                                                              | `0161`, merges after #478                                                                                                                      |

### Keeping this plan current

- A PR that implements a step of this plan updates this file in the same PR: the status table, and the step's text where the PR did something other than the text says (a deviation, a part left out, a part moved to another step). The PR description names the step ID in its title, for example `(D5)`.
- A PR that finds the plan wrong about the code (a field that already exists, a concept the plan misses) corrects the plan in the same PR, or opens an issue and links it from the step, instead of working around it in the PR description only.
- A follow-up PR without its own step (such as #517 and #519 after D5) is listed against the step it continues.
- When a decision in section 10 is taken, the row records the answer and the issue or PR where it was taken.

### Work item dates

The plan refers to these fields of `Issue` (`apps/api/plane/db/models/issue.py`); use them by these meanings and do not add another field for the same thing.

| Field                                                           | Meaning                                                                                      | Who sets it                                    |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `start_date`                                                    | planned start                                                                                | people; date shifting                          |
| `finish_date`                                                   | planned or forecast end of the work; the end of the timeline bar (since `0154`)              | people; date shifting; duration                |
| `duration`                                                      | working days from `start_date` to `finish_date`, inclusive                                   | kept in sync by `utils/work_item_duration*.py` |
| `target_date`                                                   | **due date, the deadline**. Never read or written by duration or date shifting               | people                                         |
| `completed_at`                                                  | actual end; set when the state moves to a completed group                                    | `Issue.save()`                                 |
| `due_date_at_completion`                                        | the due date as it was at completion, so later edits do not change whether the item was late | `Issue.save()`                                 |
| `dates_initialized`, `finish_date_origin`, `target_date_origin` | provenance of the first finish and due dates                                                 | API                                            |

Consequences for this plan: schedules (critical path, baselines, shifting, milestones) work on `start_date` and `finish_date`; "deadline" and "due date" always mean `target_date`; "late" means `finish_date` (planned) or `completed_at` (actual) after `target_date` or `due_date_at_completion`. Cycles have `start_date` and `end_date`, modules `start_date` and `target_date`, initiatives `start_date` and `target_date` (F1); those are periods, not deadlines in the sense above.

### Sources

| Source                                           | Where                                                                                                   | Covers                                                                                                                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Studio opakowań v5 (packaging artwork prototype) | `...\Downloads\studio-opakowan-workflow-v5` (not in the repository; ask the maintainer for the package) | versions, approval steps with unlock rules, PDF viewer, annotations, XFDF and annotated PDF export                                                            |
| Gantt-RACI-dla-IT 1.0                            | `...\Downloads\Gantt-RACI-dla-IT`                                                                       | SPEC-01 (date shifting, leftovers), SPEC-02 (RACI, departments), SPEC-03 (date modes, external wait), SPEC-04 (procedure references), `MANUAL.md`, known bugs |
| Gantt-RACI-Akceptacja                            | `...\Downloads\Gantt-RACI-Akceptacja`                                                                   | SPEC-05 (file acceptance, OK / NOK rounds), `akceptacja-demo.html`. Secondary to Studio opakowań; see section 4                                               |

The folder `Gantt-RACI-dla-IT/Procedura OSM` is an internal document. Do not commit it or its dataset to the repository; use `Demo/` for fixtures.

### Rules for every PR

- Run `git fetch origin` and branch from `origin/preview`. Open PRs only against `OSM-Piatnica/pi-plane` (`gh pr create --repo OSM-Piatnica/pi-plane`), never upstream.
- Copyright headers: new files get the OSM Piątnica header, modified upstream files keep the Plane header plus the "Modified by" line. A rename is not a modification.
- Migrations live in the `db` app and are numbered in sequence. On 2026-11-23 the latest on `preview` is `0159_initiatives`, and open PRs hold `0160` (#478) and `0161` (#480); take the next free number after those, and check `ls apps/api/plane/db/migrations` and the open PRs first. Parallel PRs will collide: the PR that merges second rebases, renumbers its migration and re-points its dependency at the then-latest one.
- Update this plan in the same PR (see "Keeping this plan current").
- Every feature needs tests: API in `apps/api/plane/tests/{unit,contract/app,contract/api}` (run through `compose-test.yaml`), web in `apps/web/tests/unit` (vitest), pure logic in the package that owns it.
- New strings go to `packages/i18n/src/locales/en/pi-extensions.json` first, then every locale. Use the `translate` skill. Polish is the primary audience.
- Primitives come from `@makeplane/propel`, composites from `@plane/blocks`. Do not bump propel in these PRs.
- Run `pnpm check` and `pnpm doctor` before pushing. Push when a step is complete, not mid-work.
- Each feature PR adds or updates a page in `docs/` (for example `docs/acceptance.md`, `docs/raci.md`).
- Attribution requested by the prototype author (see decision 9): PRs based on the Gantt-RACI packages carry the sentence "Based on the Gantt-RACI prototype and SPEC-0x by Paweł Niklewicz" in the PR description, and this trailer at the end of each commit message, after a blank line, next to any other trailers. It uses his GitHub account ([Nikpl1](https://github.com/Nikpl1)) through its `noreply` address, so GitHub credits the account without a work email appearing in history:

  ```
  Co-authored-by: Paweł Niklewicz <349763597+Nikpl1@users.noreply.github.com>
  ```

## 1. Overview

| Request                                                 | Workstream | Core idea                                                                                                                              |
| ------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 4. Specialised work item types                          | A          | `IssueType.kind` separates behaviour from naming; Epic becomes one kind among several                                                  |
| 1. SharePoint hosting                                   | B          | Document store abstraction with a SharePoint (Microsoft Graph, app-only) backend and a native backend                                  |
| 1. Acceptance and commenting on files                   | C          | "Acceptance" work item with approval steps as "Review" sub-items, immutable versions, viewer with annotations; follows Studio opakowań |
| 3. RACI, critical path, baselines, next tasks, blockers | D          | Departments on user groups, RACI per work item, schedule analysis service, baselines, focus endpoint                                   |
| 2. Lite canvas                                          | E          | A separate "My tasks" app built on the focus endpoint                                                                                  |
| 5. Initiatives and goals                                | F          | Workspace-level Goal → Initiative → Project hierarchy with progress roll-up                                                            |
| 6. Switching between modes                              | G          | The existing app rail becomes the switcher: Projects, My tasks, Approvals, Initiatives, Wiki                                           |

Three shared building blocks carry most of the plan:

1. **Type kinds (A1).** Acceptance and Review items are work items with special behaviour. That needs a general way to say "this type behaves specially", which is also the answer to request 4.
2. **Departments as user groups (D1).** The fork already has `UserGroup` with hierarchy, SSO sync (including an Entra "department" source) and group assignees. RACI and reviewer suggestions build on that instead of a new department dictionary.
3. **App rail registry (G1).** The rail (`apps/web/components/app-rail/app-rail-hoc.tsx`) has one item today. Lite, Approvals, Initiatives and Wiki each register an app there.

## 2. Workstream A: work item types (request 4)

### Concept

Today a type has `is_epic`, `is_default`, `level`, custom properties (`IssueTypeProperty`, `IssuePropertyValue`) and a workspace settings page (`settings/(workspace)/work-item-types/`). What is missing is a way to attach behaviour to a type without adding a boolean per feature.

Split a type into two things:

- **Kind**: what the system does with it. A fixed enum, set by code, not editable by users.
- **Everything else**: name, icon, properties, default template. Editable. "Bug", "Story", "Change request" are ordinary types of kind `standard` that differ only in name, icon, properties and template.

| Kind        | Level | Behaviour                                                                                                                                                             |
| ----------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `standard`  | 0     | no special behaviour; any number of user-defined types                                                                                                                |
| `epic`      | 1     | current Epic rules: no parent, excluded from module and cycle progress                                                                                                |
| `milestone` | 0     | a point in the schedule: start date equals finish date; diamond on the timeline; the due date stays a separate, optional deadline; RACI validator expects an approver |
| `approval`  | 0     | owns an `Approval` record (workstream C); state is driven by the acceptance engine                                                                                    |
| `review`    | -1    | one approval step; only as a child of an `approval` item; one approver; state is driven by the engine                                                                 |

Rules that follow from kind:

- Hierarchy: a child's level must be lower than or equal to the parent's, `epic` has no parent, `review` must have an `approval` parent. This generalises `utils/work_item_hierarchy.py:validate_work_item_parent`.
- System-managed kinds (`approval`, `review`): users cannot change the type of an existing item to or from these kinds, and cannot set the state by hand; the API rejects it with a clear error code.
- Progress: `IssueProgressManager` keeps excluding Epics and also excludes `review` items, so one acceptance counts once.
- One type per system kind per workspace (`epic`, `milestone`, `approval`, `review`), created on demand, the same way `ensure_project_epic_type` works today.

### PRs

**A1. `IssueType.kind` (API). Size M. Merged: #473.**

- Migration: add `kind` (`CharField`, choices above, default `standard`, indexed). Data migration sets `kind="epic"` where `is_epic` is true.
- Keep `is_epic` as a stored field for compatibility with upstream code and the public API; keep it in sync in `IssueType.save()` and add a check constraint `is_epic = (kind = 'epic')`. Removing the field is tracked in [#512](https://github.com/OSM-Piatnica/pi-plane/issues/512).
- Replace direct `is_epic` reads in fork code with `kind` where the code is ours (`utils/project_issue_types.py`, `utils/work_item_hierarchy.py`, `utils/epic_progress.py`); leave upstream call sites alone.
- Generalise `ensure_project_epic_type` into `ensure_project_kind_type(project, kind)`; the Epics endpoint keeps its URL and behaviour.
- Serializers expose `kind` read-only. `issue_type_assignment_error` rejects switching into or out of system-managed kinds.
- Tests: migration data test, hierarchy matrix (every parent kind against every child kind), existing Epic contract tests stay green.

**A2. Kinds in the web app. Size M.**

- `packages/types`: `TIssueTypeKind`; helper `isSystemManagedKind`.
- Type select (`components/issues/issue-modal/issue-type-select.tsx`) and switcher (`issue-details/issue-type-switcher.tsx`) hide system-managed kinds unless the caller asks for them.
- Workspace type settings show kind as a read-only badge; system types can be renamed and re-iconed but not deleted while in use.
- Replace `workItem.is_epic` checks in fork-owned components with a `kind` helper.
- Remove or wire up the unused `store/issue/epic/*` stub only if it is in the way; otherwise leave it.
- Bulk assign must keep system-managed kinds linked, like Epic types. `ProjectIssueTypeBulkAssignEndpoint` sets the whole list of a project's types, so today it unlinks an approval or review type that the list leaves out (only Epic types are kept, #460 and A1). The project type list in the web app (`components/settings/project/content/issue-types-control.tsx`) must not offer these kinds for unticking, and the endpoint must keep their links, as it does for Epic types; the acceptance engine (C1) links them through `ensure_project_kind_type`.
- Type icon, left over from the Epics port (#485 shows the icon of the type before the identifier of a work item, keyed on `is_epic`). Hangar's version went further; A2 takes the rest:
  - Built-in marks by kind. `getWorkItemTypeMarkKind` (`apps/web/helpers/work-item-type-mark.ts`) picks the mark of a type without a logo by `is_epic` (Epic mark, else a general one). Move it onto `kind`, with a built-in mark for each of epic, milestone, approval and review. Do not add a `system_key` for this, as Hangar did: `kind` is that key here.
  - `IssueTypeIdentifier` (`components/issues/issue-details/issue-identifier.tsx`) is still a name chip, used in a few modals (draft block, existing work items modal, relations). Hangar made it an icon with a tooltip. Make it use the same mark component as the identifier, so one component draws a type everywhere.
  - Icon picker on the project's type page. Hangar let project admins pick the icon in the project-level type settings; here the picker exists only in workspace type settings (`work-item-types/page.tsx`). The project type list (`components/settings/project/content/issue-types-control.tsx`) can offer it too. A type is shared by every project of the workspace, so the picker there changes the icon everywhere: say so in the UI, or leave it to workspace admins.

**A3. Type catalogue and per-type templates. Size M.**

- Seed command and "Add from catalogue" button in workspace type settings: Task (default), Bug, Story, Change request, Milestone. Each catalogue entry brings an icon, a description template and suggested properties (Bug: severity, environment, steps to reproduce; Change request: reason, impact).
- Icons of the catalogue entries and of the system types must pass the logo validation of #485: `{"in_use": "icon", "icon": {"name", "color", "background_color"}}` or `{"in_use": "emoji", "emoji": {"value"}}`, short text only. A catalogue of types with icons is this PR; the picker and the marks are A2.
- New nullable `IssueType.description_template` (HTML). The create modal pre-fills the description when the type is chosen and the description is empty.
- Filters and Group by "Type" on list, board and timeline if not already complete (check `components/issues/filters/issue-types.tsx`).
- Milestone behaviour: the serializer forces `start_date = finish_date` (duration 1; when only one of the two is sent, the other follows it); `target_date` is not touched and stays the milestone's deadline. The timeline renders a diamond at `finish_date`, red when it is after `target_date`.

**A4. Procedure references as properties (SPEC-04). Size S.**

- No new columns. Seed two text properties on the default type of a project when the project turns on "Procedure references": `procedure_ref` ("Punkt procedury") and `form_ref` ("Formularz").
- Show `form_ref` as a chip next to the name in list rows and timeline rows; add a filter by property value if the filter system does not support custom properties yet (check `rich_filters`).
- Project gets `procedure_version` and `procedure_url` (two nullable fields, shown in the project header).
- Check that project duplication (`docs/duplicating-projects.md`) copies property values; add a test.

## 3. Workstream B: SharePoint and the document store (request 1)

### Design

**Access model: app-only, least privilege.** One Entra app registration with the application permission `Sites.Selected`, granted by a SharePoint admin to the specific site or sites Pi-Plane may use. Pi-Plane authenticates with client credentials and mediates every read and write after its own permission checks.

Why not per-user (delegated) tokens: the SSO flow deliberately stores no provider tokens (`docs/sso.md`), reviewers may sign in by other means, and background jobs (reminders, checksum verification) need access without a user present. The cost is that SharePoint's own per-user permissions are not applied to access through Pi-Plane; project membership is the gate. See decision 4.

**Configuration.**

- Instance level (God Mode, `InstanceConfiguration`, encrypted): `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET` (certificate later), `SHAREPOINT_MAX_FILE_SIZE` (default 500 MB, independent of `FILE_SIZE_LIMIT`), `IS_SHAREPOINT_ENABLED`. Follow the GitHub provider example end to end: `utils/instance_config_variables/core.py`, `apps/admin/app/(all)/(dashboard)/authentication/github/`.
- Workspace level: `DocumentLibrary` (workspace, provider, `site_id`, `drive_id`, `root_path`, `web_url`, `is_default`). A workspace admin pastes a site URL; the API resolves it through Graph and stores the IDs.
- Project level: optional override of library and folder. Default folder layout: `{root_path}/{PROJECT_IDENTIFIER}/{PROJECT_IDENTIFIER}-{sequence_id}/`.

**Abstraction.** A `DocumentStore` protocol with two implementations, so development, CI and instances without SharePoint work unchanged:

| Operation                      | SharePoint (Graph)                                                    | Native (existing S3 / Azure storage)    |
| ------------------------------ | --------------------------------------------------------------------- | --------------------------------------- |
| `begin_upload`                 | `createUploadSession` on the target path, returns the upload URL      | presigned POST, as attachments do today |
| `finish_upload`                | read back driveItem: `id`, `eTag`, current version ID, size, `webUrl` | mark uploaded, read metadata            |
| `download_url`                 | short-lived `@microsoft.graph.downloadUrl`                            | presigned GET, inline                   |
| `thumbnail_url`                | `/thumbnails`                                                         | none in v1 (client renders page 1)      |
| `list_versions`, `get_version` | `/versions`                                                           | one object per version                  |
| `delete`                       | not exposed in v1                                                     | existing delete                         |

**Models** (new, not `FileAsset`, whose `asset` FileField and `asset_url` assume our own bucket):

- `Document`: workspace, project, issue (nullable), name, mime type, provider, `external_drive_id`, `external_item_id`, `web_url`, created_by.
- `DocumentVersion`: document, `number` (1, 2, ...), `external_version_id`, `etag`, size, `sha256`, `checksum_status` (pending, verified, mismatch), uploaded_by, uploaded_at. Unique (document, number). Rows are never updated or deleted by users.

**Versions and immutability.** One SharePoint file per logical document; each upload through Pi-Plane creates a new SharePoint version, and Pi-Plane records the version ID. The browser computes SHA-256 during upload (WebCrypto); a Celery task downloads the stored version and verifies it. SharePoint users can still edit the file directly, so:

- when a version is added and when a file is opened, compare the stored `etag` with the live one;
- if they differ, show "File changed in SharePoint" and let the owner adopt the change as a new version;
- a version whose checksum no longer matches is flagged, never silently served.

**Client access.** The browser uploads straight to the Graph upload session URL in chunks and downloads from the pre-authenticated download URL, the same pattern the attachment endpoints use (API issues a URL, then redirects or returns it). B1 must confirm with a real tenant that both work cross-origin from the Pi-Plane origin; if either does not, fall back to a streaming proxy endpoint in the API with range support. The rest of the plan does not depend on which path wins.

**Dependencies.** No MSAL: client-credentials token requests are one POST. Use `httpx` (already a dependency), cache the token in Redis until shortly before expiry, and put all Graph calls in one module with retry on 429 and 503 honouring `Retry-After`. There is prior Graph code to follow in `authentication/provider/oidc/groups.py`.

### PRs

**B1. Spike: Graph access from a test tenant. Size S. No merge to preview required.**

- Prove: token with `Sites.Selected`, resolve site and drive, upload session from the browser (CORS), download URL fetched by `fetch()` in the browser (CORS, range requests), thumbnails, version list, eTag behaviour after a direct edit in SharePoint.
- Output: a short note in the PR for B2 with what worked, and the chosen path (direct or proxy).
- Needs a test site and app registration from the user (decision 4).

**B2. Graph client and instance configuration. Size M. Open: #479.**

- `apps/api/plane/utils/sharepoint/{client.py,errors.py}`; config variables; God Mode page "Integrations → SharePoint" with a "Test connection" button.
- Tests with a fake Graph transport (`httpx.MockTransport`); no network in CI.

**B3. Document store and models. Size L.**

- `apps/api/plane/utils/document_store/{base.py,sharepoint.py,native.py}`; models and migration; endpoints under `workspaces/<slug>/projects/<pid>/documents/` (begin upload, finish upload, list, versions, download redirect, thumbnail redirect).
- Permissions: project members; guests follow `FileAsset.is_project_accessible_to` rules.
- Checksum verification task in `bgtasks/`.
- Contract tests run against the native store; unit tests cover the SharePoint store with the fake transport.

**B4. Workspace and project settings UI. Size M.**

- Workspace settings "Document libraries": add by site URL, pick drive, root folder, default.
- Project settings: library and folder override; link "Open folder in SharePoint".

**B5. SharePoint files as ordinary attachments (optional, after C). Size M.**

- "Upload to SharePoint" and "Link existing SharePoint file" in the attachment section of any work item, listed next to native attachments with a SharePoint badge and the viewer from C2.

## 4. Workstream C: acceptance and file review (request 1)

### Which prototype decides

**Studio opakowań v5 is the reference.** Its behaviour is implemented as described in its README and `dist/workflow.js`. Where it and SPEC-05 differ, Studio wins. Ideas that exist only in SPEC-05 are collected in PR C8 as optional extensions, each needing explicit approval before work starts.

| Topic          | Implemented (Studio)                                                                                | SPEC-05 variant, not implemented by default          |
| -------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Unit of review | artwork version; each version keeps its own copy of the workflow and its decisions                  | round                                                |
| Approvers      | named steps: name, approver, due date, order                                                        | flat list of reviewers with one deadline             |
| Order          | per step: sequential (default), after selected steps, always available                              | all in parallel                                      |
| Rejection      | one "Request corrections" action on the version; approvals pause until a new version is added       | NOK per reviewer; the round waits for every decision |
| New version    | per-step "restart after new version" (default on); with it off, a finished approval is carried over | owner picks who reviews the next round               |
| Files          | one artwork per acceptance, in successive versions                                                  | several files per round                              |
| Remarks        | comments and annotations on the version, resolve and reopen                                         | NOK reason with owner's "fixed / explained" answer   |

The user's "acceptance block with reviews as sub-items" maps directly: the Acceptance work item is the Studio project, and each approval step is a sub-item of kind `review` assigned to the approver. A step is then a real work item with an assignee, a due date, the existing due-date reminders, a place on the timeline and in "My tasks".

### Behaviour (from the Studio README)

- **Workflow.** An Acceptance item has at least one step. Steps can be added, reordered and removed. Each step has a name, an approver, a due date, an unlock rule and a "restart after new version" switch. A bulk switch turns restart on or off for all steps. A new Acceptance item starts with one step assigned to the owner.
- **Unlock rules.**
  - Sequential: available after all earlier steps.
  - After selected steps: available once every chosen step is approved; no chosen steps means available from the start; steps with the same conditions unlock together.
  - Always available: can be approved at once, and is still required for completion.
- **Validation.** The configuration is rejected if the rules form a cycle or point at a step that no longer exists. A step that others depend on cannot be removed until those dependencies are removed.
- **Approving.** Every unlocked step has "Approve"; "Choose approval" lists all currently available steps. Conditions are checked again when the decision is saved. Approvals are possible only on the latest version. All steps are required; when all are approved the version is approved and the Acceptance item completes.
- **Requesting corrections.** One action on the latest version. It pauses all approvals until a new version is uploaded. Who may do it and whether a comment is required is not defined by the prototype (it has no accounts); see decision 2.
- **New version.** Steps with restart on need approval again. A step with restart off keeps its approval if its name, approver and unlock conditions are unchanged; the carried decision shows author, date and the version it was given on. Unfinished steps always need approval.
- **Changing the workflow of an existing item.** Changing order, names, approvers or unlock conditions resets approvals of the latest version. Changing due dates or restart switches keeps them. Older versions keep their own configuration and decisions and are read-only.
- **Versions.** Immutable and numbered, each with thumbnail, author and date. PDF, JPG, PNG and WebP are previewed; the original bytes are always what "Download" returns.
- **Remarks.** Comments and annotations belong to a version and a page and do not move to the next version. They can be edited, resolved and reopened. History records the changes.
- **States.** The engine owns status and maps it onto state groups, so no project needs special states:

  | Status                       | State group of the Acceptance item |
  | ---------------------------- | ---------------------------------- |
  | preparation (no version yet) | unstarted                          |
  | in approval                  | started                            |
  | corrections requested        | started                            |
  | approved                     | completed                          |

  A step sub-item is `unstarted` while locked or paused, `started` while available, `completed` when approved (including carried approvals). It reopens when a new version requires it.

- **Audit.** Every event (version added, approved, corrections requested, workflow changed, approvals reset) is written to work item activity and to an append-only `ApprovalEvent` table.

### Models

- `Approval`: issue (one-to-one), document (from B3), status, current_version.
- `ApprovalStep`: issue (one-to-one, the step sub-item), approval, name, approver, sort_order, unlock_mode (sequential, custom, always; default sequential), depends_on (M2M to self), restart_on_new_version (default true). The step's due date is the sub-item's due date (`target_date`); the sub-item's start and finish dates are its planned schedule, as for any work item, and are not set by the engine.
- `ApprovalVersion`: approval, number, document_version, workflow_snapshot (JSON copy of the steps as they were), review_blocked, approved_at, approved_by. Unique (approval, number).
- `ApprovalDecision`: version, step, decided_by, decided_at, carried, source_version, carried_from_version. Unique (version, step).
- `CorrectionRequest`: version, requested_by, comment, created_at.
- `Annotation`: document_version, page, kind (page, pin, rect), x, y, w, h (relative, 0 to 1), body, author, resolved_by, resolved_at, parent (for replies).
- `ApprovalEvent`: approval, version, actor, verb, payload JSON, created_at.

Annotations are stored as database rows, not as XFDF blobs (the prototype's canonical form in IndexedDB). This is a storage change only: rows can be queried and used for notifications, and the XFDF and annotated-PDF exports produce the same output as the prototype. The original file is never modified.

### PRs

**C1. Acceptance engine (API). Size L. Needs A1, B3.**

- Models, migration, and a service module `utils/approval/engine.py` that is a port of `dist/workflow.js`: `prerequisites`, `validateWorkflow`, `availableApprovals`, `isComplete`, `startVersion` (carry logic), `configureLatest` (reset rules), `approveNext`. Keep the function boundaries so the two can be compared.
- Creating an item of kind `approval` creates its `Approval` with one default step; adding a step creates the sub-item and its `ApprovalStep`.
- Endpoints under `.../issues/<id>/approval/`: workflow (read, replace), `versions/` (add), `versions/<n>/`, `steps/<id>/approve/`, `request-corrections/`, `events/`.
- Permissions: the owner (assignees of the Acceptance item) and project admins configure and upload; only a step's approver approves it.
- Tests: every rule in the README sections "Workflow akceptacji" and "Równoległe i zawsze dostępne akceptacje", including the worked example (Treść from the start; Prawne and Brand need Treść; Prepress needs both; Właściciel always available), the reset-versus-keep rules on configuration change, and carried decisions.

**C2. Document viewer (web). Size L. Needs B3 for real files; can start against the native store.**

- Add `pdfjs-dist` (Apache-2.0; the prototype uses 4.10.38) and `pdf-lib` (MIT; 1.17.1) to the pnpm catalog; load both lazily so they stay out of the main bundle. Add the licences to the third-party notices.
- `apps/web/components/document-viewer/`: PDF and raster image (JPG, PNG, WebP) rendering, page picker, zoom (minus, plus, fit, 100%, Ctrl + wheel), scrolling when zoomed, thumbnails of the first page.
- Compare two versions side by side with independent zoom and page in each panel, rendered from the original files; resizable window.
- Other formats (AI, PSD, TIFF, Office): show the SharePoint thumbnail and "Open in SharePoint"; no annotations. Never inline SVG; render it through `<img>` only.
- Wire the viewer into ordinary attachments for PDFs and images ("Preview"), replacing `window.open` in `attachment-list-item.tsx`.

**C3. Annotations and export. Size L. Needs C2.**

- API: CRUD on annotations per document version; resolve and reopen; replies.
- Web: Browse mode plus three tools (page comment, comment at a point, mark an area); markers use relative coordinates and scale with the page; comments for the current page listed under the preview; read-only in compare view and on older versions.
- Pure logic in `packages/utils/src/annotations/` with tests, ported from `dist/annotation-export.js`: coordinate conversion, XFDF serialise and parse (zero-based pages, source file name, IDs, authors, dates, Review / Completed for resolved remarks).
- Export: XFDF download; "PDF with comments" built in the browser with pdf-lib as standard Text and Square annotations with appearance streams, always starting from the original bytes, keeping annotations already present in the uploaded PDF.

**C4. Acceptance UI on the work item. Size L. Needs C1, C2.**

- Acceptance panel in work item detail and peek view: version list with thumbnail, author and date; steps with status, approver and due date; "Approve" per unlocked step; "Choose approval"; "Request corrections"; "Add version".
- Workflow editor ("Configure workflow"): add, reorder, remove steps; name, approver, due date; unlock rule with prerequisite picker; restart switch per step and the bulk switch; validation messages for cycles and missing dependencies; a warning before a change that resets approvals.
- Older versions shown read-only with their own steps and decisions; carried decisions show author, date and source version.
- History tab from `ApprovalEvent`.
- Timeline bar label: "v2 · 3/5 approved", or "corrections requested".
- Hide the manual state control for system-managed kinds.

**C5. Notifications. Size S. Needs C1.**

- Events to notifications and email through `notification_task` and the digest: step unlocked → its approver; corrections requested → owner and all approvers; new version → approvers whose steps need approval; approved → owner, approvers, subscribers.
- Due dates of steps use the existing work item due reminder; nothing new is built for reminders.
- Webhook events `approval.version_added`, `approval.step_approved`, `approval.corrections_requested`, `approval.approved`.

**C6. Approvals app. Size M. Needs C4, G1.**

- Rail app "Approvals" following the Studio screens: cards (thumbnail, version, stage, owner, due date), list and Kanban by stage, search and filters, CSV export of the list.
- Sections "Waiting for my approval", "Owned by me", "All".
- Full-screen Layout / Artwork page: versions on the left, viewer in the middle, steps and comments on the right.

**C8. SPEC-05 extensions (optional; each item needs explicit approval first). Size varies.**
None of these is in the Studio prototype. Do not start any of them without a decision recorded in section 10.

- Several files in one acceptance (a package per version).
- A reason attached to each individual rejection, and the owner's "fixed / explained" answer shown to the approver on the next version.
- "Wait for everyone" mode: corrections collected from all approvers before the version is sent back.
- Approvers suggested from RACI (needs D2).
- Delegation of a step to someone in the same department (needs D1).
- Escalation after the due date; withdrawal of a version sent by mistake.
- Notifications by RACI letter for acceptance events (needs D3).

## 5. Workstream D: RACI and scheduling (request 3)

Already delivered before this plan: dependency shifting with confirmation, relation types with lag, parent date roll-up, working days, and the split of the planned finish (`finish_date`) from the due date (`target_date`, migration `0154`; see "Work item dates" in section 0). This workstream covers what the specs still list as missing. SPEC-01 and SPEC-03 speak of a single end date or "deadline"; map them onto the two fields here, never onto a new one.

### Design choices

- **Departments are user groups.** SPEC-02 proposes a new `WorkspaceDepartment`. Use `UserGroup` instead, with `kind` (group, department), `code`, `color`, `sort_order` and `is_active`. A person's department is the active department group they belong to; there is no field on `WorkspaceMember` (changed during D1, #476). This deviates from SPEC-02 on purpose (decision 5) and avoids two parallel dictionaries of the same organisation.
- **Letters are stored neutrally**: `responsible`, `approver`, `consulted`, `informed`. Locales display them: Polish O / Z / K / I, English R / A / C / I.
- **Schedule analysis runs on the server**, in one module that reuses the graph and working-day code of `utils/issue_reschedule.py`. The web app only draws results.

### PRs

**D1. Departments. Size M. Merged: #476.**

- Delivered: migration `0157_departments`; workspace settings "Departments" (list, code, colour, order, switch, import from a pasted list), managed by workspace admins only; "Department" column in member settings; members are managed on the Groups page. A person belongs to at most one active department (the API answers 409 or 400 otherwise); SSO sync joins the first department the provider lists and replaces one set by hand. See `docs/departments.md`.
- Changed from the plan: no `WorkspaceMember.department` field, and no picker in onboarding, on invitation or at sign-in; workspace admins assign people. Whether a person may be in several departments is [#508](https://github.com/OSM-Piatnica/pi-plane/issues/508); D2 and D9 must not rely on "the" department of a person more than that issue settles.

**D2. RACI on work items (SPEC-02). Size L. Needs D1.**

- `IssueRaci` (issue, group, role), unique (issue, group); several `responsible` allowed. `group` is a department group (`UserGroup.kind = department`). Project switch "RACI" in feature toggles.
- Endpoints for read and bulk set; activity entries; included in project duplication.
- Web: RACI section in work item detail; list columns for responsible, approver, consulted; display property; filter "my department" and filter by role; timeline bar coloured by the responsible department (two colours for two).
- Edit rights: project admins and the project lead (decision 10).

**D3. RACI notifications and validation. Size M. Needs D2.**

- Workspace setting with the event-by-role matrix from SPEC-02, defaults as in the spec. `notification_task` adds members of matching departments to recipients.
- "Who will be notified" preview in work item detail.
- Project warnings panel: item without a responsible department, milestone without an approver, department with a letter but no members, item with no predecessor, item nothing depends on.

**D4. Import and export. Size S. Needs D2.**

- Importer: `RACI` column (`O:RM;K:PR;Z:ZA`, both Polish and English letters accepted); labels of the form `O:XX` become RACI rows when RACI is on.
- Exporter writes the same column.
- Fix the known bug: importer accepts `module_name` as well as `modules` (`community_work_item_import.py`), with an export-then-import test. Verify the bug on a running instance first; the report was made from reading code.

**D5. Schedule analysis and critical path. Size L. Merged: #475, #517; #519 open.**

- Delivered (#475): `utils/schedule_analysis.py`, a forward and backward pass over work items with both `start_date` and `finish_date`, and their relations (all four types, lag, working days). Per item: earliest and latest start and finish, total float, `is_critical`, and `needed_by`, the latest finish that lets every open work item downstream meet its due date (`target_date`). Due dates never make a work item critical; they only feed `needed_by`. Completed and cancelled items are fixed points. Cycles are reported and the rest is analysed.
- Endpoint `projects/<id>/schedule-analysis/` (optional module or cycle scope). Changed from the plan: no cache (invalidation would have to follow too many changes) and no pagination; a cap of 2000 dated work items, with `truncated` in the answer.
- Web: "Critical path" toggle on the timeline; Float and "Needed by" in work item detail; the Float display property for list, kanban and spreadsheet (#517); a "Critical path" filter (#519). Rules and limits are in `docs/critical-path.md`.
- Open: sorting by Float ([#518](https://github.com/OSM-Piatnica/pi-plane/issues/518)).

**D6. Baselines. Size M.**

- `ProjectBaseline` (project, name, created_by, is_active) and `BaselineItem` (baseline, issue, start_date, finish_date, target_date, state group). "Save baseline" on the timeline; one active baseline per project, older ones kept.
- The ghost bar and the variance use the schedule, `start_date` to `finish_date`, as the timeline bar does. The saved `target_date` is shown as a separate marker so a moved deadline is visible, and it does not count as schedule variance.
- Timeline draws a grey ghost bar under each bar and shows the difference in working days; list column "Variance"; baseline picker.
- "What if" (unsaved shifts compared with the baseline) is out of scope for the first version.

**D7. Date modes and external wait (SPEC-03). Size L. Needs D5.**

- SPEC-03's modes say which dates are firm. They map onto the existing fields; D7 adds no date field and no estimated duration (`finish_date` is the estimate, `duration` its length):

  | Mode             | Firm                        | Estimated                      | Behaviour                                                                                              |
  | ---------------- | --------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------ |
  | `both` (default) | `start_date`, `finish_date` | none                           | today's behaviour                                                                                      |
  | `start_known`    | `start_date`                | `finish_date` (and `duration`) | a predecessor or relation that moves the finish gives a warning, not a relation conflict               |
  | `deadline_known` | `target_date`               | `start_date`, `finish_date`    | the latest start comes from D5; predecessors that push `finish_date` past `target_date` give a warning |

- New fields: `date_mode` (the three values above) and `is_external_wait`. Before adding `date_mode`, check whether it can be derived (for example `deadline_known` = a due date and no start date) and store it only if people need to set it against the data.
- Timeline rendering for both modes and a hatched bar for external wait; filter "waiting on external parties".
- Forecast view (SPEC-03 part 4) is deferred.

**D8. SPEC-01 leftovers. Size M. Open: #478 (cause in the history, the project setting, sub-item behaviour pinned by tests); the deadline warning is left over as D8b.**

- Reschedule dialog warns when a shifted item's new `finish_date` passes its due date (`target_date`): "DEMO-41 will exceed its deadline by 3 days", counted in working days. Not in #478, whose description says there is no deadline separate from the due date yet; the due date is that deadline, so this needs no D7 and is a small follow-up PR (D8b).
- Activity entry of a shifted item links to the item that caused the shift.
- Project setting "Offer to shift dependent items" (default on).
- Check that the cascade covers sub-items when a parent with roll-up is moved. #478 found it does not (roll-up is display only) and changed nothing; whether sub-items should follow, whether a rolled-up span should count in dependencies, and whether sub-items inherit a parent's predecessors are decision 15.
- Shifting backwards stays out of scope.

**D9. Focus endpoint: next tasks and blockers. Size M. Needs D2 for the department parts.**

- `workspaces/<slug>/focus/` (optionally per project) returns, for the current user and their department:
  - next: my open items ordered by `start_date`, then `finish_date`, startable ones first;
  - blocked: my items with unfinished predecessors, with who holds the predecessor;
  - waiting on us: other people's items blocked by mine;
  - to approve: approval steps available to me (from C1) and items where my department is the approver;
  - overdue: open items whose due date (`target_date`) has passed, and open items whose `finish_date` has passed.
- Work item detail gains "Blocked by" and "Blocking" summaries with owner and date, and a "Next" hint when an item completes.
- Web: "My view" panel in the project (SPEC-02) and the data source for workstream E.

## 6. Workstream E: Lite (request 2)

### Design

Lite is a separate app in the rail ("My tasks"), not a switch that hides parts of the full interface. A hidden-features mode has to be maintained on every screen and leaks whenever a new control is added; a small separate surface over the same data does not. Both apps open the same work items, so nothing is duplicated in the API.

What Lite shows:

- **Today and next**: the D9 lists as plain sections (To do now, Waiting on someone, Someone is waiting on me, To approve, Overdue).
- **Simple board**: three columns by state group (To do, In progress, Done) across the user's projects; drag changes state to the project's default state of that group.
- **Simple planning**: quick add with name, project, due date and "after task ..." (creates a `blocked_by` relation, nothing else); a compact two-week calendar strip. No lag, no other relation types, no timeline.
- **Simple detail**: title, description, state, dates, assignee, checklist of sub-items, comments, attachments with the viewer, "blocked by / blocking", and the review decision when the item is a review. No cycles, modules, estimates, labels, properties or activity filters. A link "Open in Projects" for everything else.

Who gets it:

- `WorkspaceMember.default_app` (projects, lite, approvals; nullable). Workspace setting for the default per role, for example guests land in Lite.
- The user can switch at any time through the rail unless a workspace admin restricts a role to Lite (`WorkspaceMember.allowed_apps`, optional, later).

### PRs

**E1. Lite home (Today and next). Size M. Needs D9, G1.**
**E2. Simple board and quick add with "after task". Size M.**
**E3. Simple work item detail. Size M.** Reuse the stores of the existing detail view; new presentation only.
**E4. Default app per member and per role. Size S. Needs G2.**
**E5. Mobile layout pass for Lite. Size S.** Lite users are the likeliest to open a link from an email on a phone.

## 7. Workstream F: initiatives and strategic goals (request 5)

### Design

One model, two levels: a **goal** states an outcome for a period; an **initiative** is a body of work toward it; projects (and optionally Epics) belong to initiatives. An initiative does not need a goal, and a project can belong to more than one initiative.

- `Initiative`: workspace, `kind` (goal, initiative), parent (a goal, nullable, only for kind initiative), name, description, lead, start_date, target_date, status (planned, active, paused, completed, cancelled), health (on track, at risk, off track), logo_props, colour, sort_order.
- `InitiativeProject` (initiative, project) and `InitiativeEpic` (initiative, issue of kind epic).
- `InitiativeUpdate`: initiative, author, health, text, created_at (periodic status notes).
- Progress rolls up from projects through `Issue.progress_objects`, so Epics and reviews are not double counted.
- Permissions: workspace admins and members manage; a user sees progress numbers only for projects they can access, and the response says when the roll-up is partial.

Leftovers to reuse: the reserved slug `initiatives`, `EFileAssetType.INITIATIVE_DESCRIPTION`, `initiativesSidebarCollapsed` in the theme store.

### PRs

**F1. Models and API. Size M. Merged: #472.** Decisions taken in review: delete is limited to workspace admins, the lead and the creator; workspace admins see every initiative and can link and unlink any project and Epic; a goal returns the de-duplicated Epics of its initiatives. See `docs/initiatives.md`.
**F2. Initiatives app: list, detail, add projects and Epics, status updates. Size L. Needs G1.**

- Includes one API addition deferred from F1: a second progress figure for the Epics linked to an initiative, separate from the main one.
  - The main figure stays "work items in the linked projects". Linked Epics are not added to it, so an Epic inside a linked project is not counted twice.
  - The Epic figure is computed from each linked Epic's child work items with the existing Epic progress code (`utils/epic_progress.py`), under the same visibility rule as projects (inaccessible Epics are counted, not listed).
  - It serves an initiative that owns one Epic of a larger shared project without owning the whole project. Settle the response shape together with the screen that shows it.
    **F3. Project list: filter and group by initiative; initiative chip in the project header. Size S.**
    **F4. Roadmap timeline: initiatives and their projects on a time axis (reuse `store/timeline/` and the gantt chart blocks). Size M.**
    **F5. Goals: goal level, progress across initiatives, optional target metric (name, start, target, current value). Size M.**

## 8. Workstream G: navigation (request 6)

### Recommendation

Put the switcher on the left, in the app rail that already exists, and keep the top bar for global actions. This is the common pattern in tools of this kind: a narrow vertical rail of apps, a contextual sidebar that belongs to the chosen app, and a top bar with search, create and notifications. It scales to more apps than top tabs do, keeps the full width for timelines and the document viewer, and matches what users already have (`AppRailRoot`, `Profile.is_app_rail_docked`).

| Rail app    | Contextual sidebar                                                         | Source   |
| ----------- | -------------------------------------------------------------------------- | -------- |
| Projects    | today's sidebar: home, inbox, your work, stickies, drafts, views, projects | existing |
| My tasks    | none, or a short list: Today, Board, Calendar                              | E        |
| Approvals   | Waiting for me, Sent by me, All                                            | C6       |
| Initiatives | goals and initiatives tree                                                 | F2       |
| Wiki        | workspace pages tree plus project pages                                    | G4       |

"Modes" are therefore apps. The remembered choice is the app the user lands in, not a flag that changes how each screen behaves.

Stickies stay under Projects and Home (they are personal notes, not a destination with its own navigation), with a quick "New sticky" in the top bar's create menu.

### PRs

**G1. App rail registry. Size M. Merged: #474.**

- Replace the single hard-coded item in `components/app-rail/app-rail-hoc.tsx` with a registry: key, label, icon, route prefix, `isEnabled(workspace, user)`, sidebar component. Route groups per app next to `(projects)` in `app/(all)/[workspaceSlug]/`.
- Rail shows only enabled apps; with one app it keeps today's behaviour.
- Keyboard shortcuts and command palette entries for switching apps.

**G2. Preferences. Size S. Needs G1. Open: #480 (with G3).**

- `WorkspaceMember.default_app`; landing redirect after sign-in; last used app remembered per workspace; rail order and hidden apps through the existing `WorkspaceUserPreference` pinning mechanism and the customise dialog.

**G3. Workspace feature switches. Size S. Open: #480 (with G2).**

- There is no workspace feature model today. Add `WorkspaceFeature` (or boolean fields on `Workspace`) for: lite, approvals, initiatives, wiki, RACI. Workspace settings page "Features". The rail registry reads it.

**G4. Workspace wiki. Size L. Can be last.**

- `Page.is_global` and the `wiki` i18n namespace exist but there is no workspace route. Add workspace-level pages (`/:slug/wiki`), a tree with nesting, and a section listing project pages the user can access.
- Check the live server (`apps/live`) and page permissions for pages without a project before sizing this further; treat this PR as a spike plus implementation.

**G5. Onboarding and empty states. Size S.**

- First-run hint that explains the rail; empty states in each app that say what it is for and link to the full Projects app.

## 9. Order and parallel work

```
Wave 1 (parallel):  A1   B1   D1   G1   D5   F1          (done except B1, which waits for a test tenant)
Wave 2:             A2   B2   D2   G2 G3   D6   D8 D8b   F2
Wave 3:             B3 B4   C2   D3 D4   D9   A3   F3
Wave 4:             C1   C3   D7   E1 E2   A4   F4
Wave 5:             C4   C5   E3 E4   F5
Wave 6:             C6   E5   B5   G4 G5
Later, on approval: C8
```

Hard dependencies:

- C1 needs A1 and B3. C4 needs C1 and C2. C6 needs C4 and G1.
- D2 needs D1. D3, D4 and the department parts of D9 need D2. D7 needs D5.
- E1 needs D9 and G1. E4 needs G2.
- F2 needs G1.
- Workstream C does not depend on workstream D. Only the optional C8 items do.

First usable slices, in the order worth demonstrating:

1. Critical path and baselines on the timeline (D5, D6): no dependencies, visible at once.
2. RACI with departments and the importer (D1, D2, D4): the Procedura OSM template can be imported with roles.
3. Acceptance on the native store (A1, C1, C2, C4 with B3's native backend), then SharePoint switched on (B2, B4).
4. My tasks (D9, G1, E1 to E3).

## 10. Open decisions

Each has a default the plan assumes.

| #   | Decision                                                                                                                                                         | Default in this plan                                                                                                     | Affects          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| 1   | Does the acceptance module replace the PowerApps flow, or only start it and receive the result? (Asked in SPEC-05.)                                              | Replace; expose webhooks so Power Automate can react                                                                     | C1, C5           |
| 2   | Who may request corrections, and is a comment required? (Studio has no accounts, so it does not say.)                                                            | The owner and any approver of a currently available step; needs a comment or at least one open annotation on the version | C1, C4           |
| 12  | Which SPEC-05 extensions to adopt, if any (list in C8)?                                                                                                          | None                                                                                                                     | C8               |
| 3   | Do people outside the organisation (agencies, printers) review files?                                                                                            | Not in the first version; members and guests only                                                                        | C, B permissions |
| 4   | SharePoint access: app-only with `Sites.Selected`, or per-user delegated? Which site and who registers the app?                                                  | App-only; needs a test site and app registration before B1                                                               | B                |
| 5   | Departments as user groups instead of the new `WorkspaceDepartment` of SPEC-02?                                                                                  | Taken: user groups with kind "department", no per-member field (#476)                                                    | D1, D2           |
| 6   | Polish RACI letters O / K / I / Z shown per locale over neutral stored roles?                                                                                    | Yes                                                                                                                      | D2, D4           |
| 7   | Lite as a separate app, not a toggle on the full interface?                                                                                                      | Separate app                                                                                                             | E, G             |
| 8   | Goal → Initiative → Project, with a project allowed in several initiatives?                                                                                      | Yes                                                                                                                      | F                |
| 9   | Honour the attribution request in the Gantt-RACI packages (credit sentence in the PR description, co-author trailer in commits)?                                 | Yes, for PRs that actually use them: workstream D, and C8 if adopted                                                     | D, C8            |
| 10  | Who may edit RACI on a work item?                                                                                                                                | Project admins and project lead                                                                                          | D2               |
| 11  | Maximum file size for SharePoint documents?                                                                                                                      | 500 MB                                                                                                                   | B2               |
| 13  | One department per person, or several? ([#508](https://github.com/OSM-Piatnica/pi-plane/issues/508))                                                             | One (as merged in D1)                                                                                                    | D2, D3, D9       |
| 14  | Sort lists by Float? ([#518](https://github.com/OSM-Piatnica/pi-plane/issues/518))                                                                               | No; Float is read-only, the critical path filter (#519) covers "show me what is critical"                                | D5 follow-ups    |
| 15  | Sub-items and a moved parent (#478): should sub-items follow, should a rolled-up span count in dependencies, should sub-items inherit the parent's predecessors? | No change: roll-up stays display only                                                                                    | D8, D7           |

## 11. Risks

- **Browser access to Graph upload and download URLs.** Both are designed for this, but it has not been tried from this app's origin and tenant. B1 settles it; the fallback is an API proxy.
- **Files changed or deleted directly in SharePoint.** Handled by eTag and checksum checks, not prevented. Retention or version-trimming policies on the library can remove old versions; document the required library settings in `docs/sharepoint.md`.
- **System-managed states.** Projects with unusual state sets (no state in a group) need a fallback; the engine must fail with a clear message, not pick a random state.
- **Upstream merges.** `IssueType`, `Issue` and the sidebar are upstream files. Keep changes to them small and additive; put logic in fork-owned modules.
- **Bundle size.** pdf.js and pdf-lib are large; they must be loaded only when the viewer opens. Check with `pnpm doctor`.
- **Schedule analysis cost.** D5 computes per request without a cache, with a cap of 2000 dated work items (`MAX_ANALYSED_ITEMS`). Watch response times on the largest projects before adding callers (D7, D9, Lite); a cache needs the invalidation list in `docs/critical-path.md`.
- **Two end dates.** `finish_date` (planned end) and `target_date` (deadline) are easy to confuse, and the specs and prototypes use one word for both. Every step that mentions a date names the field; see "Work item dates" in section 0.
- **Migration collisions** between parallel PRs; renumber at merge.
- **Prototype gaps.** Studio has no accounts, roles or notifications, so permissions and recipients in workstream C are this plan's additions, not the prototype's; they are marked as such in section 4 and decision 2.
- **Notification volume.** RACI matrix and acceptance events add notifications; route them through the existing digest and respect user preferences.
