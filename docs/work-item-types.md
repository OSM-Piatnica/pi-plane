# Work item types and kinds

A work item type has two sides:

- **Kind**: what the system does with work items of the type. A fixed list, set by code. Users cannot edit it.
- **Everything else**: name, icon, description, custom properties, the projects that use the type. Editable in **Workspace settings → Work item types**. "Bug", "Story" and "Change request" are ordinary types of the `standard` kind that differ only in these.

## Kinds

| Kind        | Level | Behaviour                                                                                               |
| ----------- | ----- | ------------------------------------------------------------------------------------------------------- |
| `standard`  | 0     | No special behaviour. A workspace can have any number of these.                                         |
| `epic`      | 1     | Groups other work items: no parent, left out of module and cycle progress. See [Epics](epics.md).       |
| `milestone` | 0     | A point in the schedule: start equals finish, a diamond on the timeline. See [Milestones](#milestones). |
| `approval`  | 0     | Reserved for acceptance work items. System-managed.                                                     |
| `review`    | -1    | One step of an approval: only as a child of an `approval` work item. System-managed.                    |

A work item without a type behaves like the `standard` kind.

## Rules that follow from the kind

**Hierarchy.** Checked by the server for the app, the public API, the sub-work item endpoint and the work item import:

- an `epic` has no parent;
- a `review` must have an `approval` parent, so it cannot be created without one, moved elsewhere or detached;
- a child's level is never above its parent's level, so a `review` has no children.

| Parent ↓ / Child → | standard | epic | milestone | approval | review |
| ------------------ | -------- | ---- | --------- | -------- | ------ |
| standard           | yes      | no   | yes       | yes      | no     |
| epic               | yes      | no   | yes       | yes      | no     |
| milestone          | yes      | no   | yes       | yes      | no     |
| approval           | yes      | no   | yes       | yes      | yes    |
| review             | no       | no   | no        | no       | no     |

**System-managed kinds** (`approval`, `review`). The type of an existing work item cannot be changed into or out of these kinds; taking the type off (`type_id: null`) counts as a change out of the kind. The API answers `400` with `{"error": "...", "error_code": "WORK_ITEM_TYPE_SYSTEM_MANAGED"}`. A new work item can be created with such a type. The work item import does not assign these types: the row comes in without a type, with a warning.

Only the feature that owns a system-managed type links it to a project (`ensure_project_kind_type`, which works on the models directly). The API refuses to manage these types by hand, with the same `400` and `error_code` `WORK_ITEM_TYPE_SYSTEM_MANAGED` and a fixed `error` message:

| Request                                                                      | Refused                                                                                                                                                                                    |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DELETE /api/workspaces/<slug>/issue-types/<id>/`                            | always, whether work items use the type or not                                                                                                                                             |
| `PATCH /api/workspaces/<slug>/issue-types/<id>/`                             | `is_active: false`; a `project_ids` list that links or unlinks a project (a list equal to the current links, as the type form sends it back, is fine; links to archived projects are kept) |
| `POST /api/workspaces/<slug>/projects/<project_id>/issue-types/`             | linking the type to a project                                                                                                                                                              |
| `DELETE /api/workspaces/<slug>/projects/<project_id>/issue-types/<link_id>/` | unlinking the type from a project                                                                                                                                                          |
| `PATCH /api/workspaces/<slug>/projects/<project_id>/issue-types/<link_id>/`  | `is_default: true`: such a type is never a project's default                                                                                                                               |

The name, icon (`logo_props`), description and custom properties stay editable. `kind` is read-only, so the type endpoints cannot create a system-managed type or move a type into or out of these kinds. A project template finds its work item types by name: an entry with the name of a system-managed type is skipped (not linked, no second type with that name is made) and the rest of the template is applied; `POST /api/workspaces/<slug>/projects/<project_id>/issue-setup/from-project-template/` lists the skipped names in `skipped_work_item_types`.

**Progress.** `epic` and `review` work items are left out of the progress numbers of modules and cycles: an Epic is counted through its children, and an acceptance counts once, through its `approval` work item. They still show in the lists.

## Milestones

A work item of the `milestone` kind lasts one day. The server keeps its start date equal to its finish date (the app API, the public API, drafts and the timeline's date endpoint):

- when a request sends only one of the two, the other follows it;
- when it sends both, the finish date decides; a cleared finish with a start sent keeps the start;
- a duration that is sent is dropped (the dates make it 1);
- a work item whose type changes to a milestone is collapsed onto its finish date (else its start date).

The due date (`target_date`) is never touched: it stays the milestone's deadline. Date shifting (dependents moved after a predecessor, sub-work items following their parent) keeps a milestone at one day.

On the timeline a milestone is a diamond at its finish date, red when the finish is after the due date; it can be moved but not resized. The date fields of the detail page and the create form move start and finish together, as the server does.

## Catalogue and description templates

**Workspace settings → Work item types → Add from catalogue** offers ready-made types: Task (made the workspace's default type when it has none), Bug, Story, Change request and Milestone. Each brings an icon, a description, a description template and suggested custom properties (Bug: severity, environment, steps to reproduce; Change request: reason, impact). The catalogue is written in English and Polish; the dialog uses the app's language, and other languages get English. The added types are not linked to any project.

Adding an entry never makes a second type:

- Task, Bug, Story and Change request are skipped when the workspace has a type with their name in either language;
- Milestone is the workspace's system type of the `milestone` kind, the one `ensure_project_kind_type` links (one per workspace). When the workspace already has one, the catalogue fills in its empty icon, description and template and adds the suggested properties it lacks; what an admin set stays.

The same is available to operators: `python manage.py seed_work_item_type_catalogue <workspace_slug> [--keys bug story] [--language pl]`.

Every type can have a **description template** (HTML, edited in the type form). The create form puts it into the description of a new work item when its type is chosen and the description is empty; switching to another type replaces a template nobody edited, and never replaces text a person wrote. The server sanitises the template like a work item description.

API: `GET /api/workspaces/<slug>/issue-types/catalogue/?language=pl` lists the entries with `existing_type_id`; `POST` the same URL with `{"keys": ["bug", "milestone"], "language": "pl"}` answers each entry's `status` (`created`, `exists` or `updated`) and type. `description_template` is a field of the type endpoints.

## `kind` and `is_epic`

`is_epic` is the older flag for the Epic kind. Upstream code and the public API read it, so it stays, and it is always equal to `kind == "epic"`:

- the model keeps the two in step when a type is saved; a changed `kind` decides, otherwise `is_epic` moves a type between `standard` and `epic`;
- a database check constraint (`issue_type_is_epic_matches_kind`) refuses a write that sets only one of them, which covers code that skips `save()` (`QuerySet.update`, `bulk_create`, `bulk_update`). Such code has to write both fields.

The type endpoints return `kind` as a read-only field. The type form can still switch `is_epic` on a `standard` or `epic` type that no work item uses; it is refused on the other kinds.

## System types

`epic`, `milestone`, `approval` and `review` each have one type per workspace that the system uses: the oldest active type of the kind, created on demand under the name of the kind (it can be renamed afterwards) and linked to the project that needs it. Creation takes turns per workspace (a lock on the workspace row), so two requests at the same moment end up with one type. There is no unique constraint: admins can still make more types of the Epic kind. For Epics this is the **Epics** switch in the project's feature settings; the other kinds are linked by the features that use them.

## In the web app

- **Choosing a type.** The type select of the create and edit form and the type switcher of a work item (detail page and peek view) do not offer the types of a system-managed kind. A work item that already has such a type shows it read-only, with a lock and a short explanation. Epic and milestone types are offered like any other type: choosing the Epic type is how an Epic is made.
- **A refused change.** When the server answers `WORK_ITEM_TYPE_SYSTEM_MANAGED`, the app shows a translated message and puts the previous type back.
- **Workspace settings → Work item types.** A type of a kind other than `standard` has a badge with the kind. The kind cannot be edited. A system-managed type can be renamed and given another icon, description and properties; its **Active** switch, its **Remove** button and its project list are switched off, with the reason shown. The "Epic type" switch is offered for the `standard` and `epic` kinds only.
- **Type lists of a project** (project settings → Features, and the list shown when a project is created). They do not list system-managed types. The bulk assignment endpoint behind them keeps the links of system-managed types that the list leaves out (as it does for Epic types), does not link one that the list names, and never makes one the default type of the project. Epic types are still owned by the **Epics** switch. The icon of a type is picked in workspace settings only: a type is shared by every project of the workspace, so a picker on a project's page would change it everywhere.
- **The type mark.** One component draws a type next to the identifier of a work item and on its own (drafts): the icon an admin picked, else a built-in mark for the kind (Epic, milestone, approval, review), else a general one.
- **Project templates.** An additional type whose name is the name of a system-managed type of the workspace is marked in the editor and is not saved with the template.
- **Filters and grouping.** System-managed types appear in the type filter and in "Group by type" under their names, like any other type.

The server refuses a change of the type of a work item and keeps system-managed types linked through the bulk assignment. The rest are guards of the web app only: the server does not yet refuse deleting or deactivating a system-managed type, unlinking it from a project through the project list of the type form or the single link endpoint, or linking it through a template entry that has its name.

## For developers

- `TIssueTypeKind` and `kind` on `TIssueType`: `packages/types/src/issue-type.ts`. `kind` is optional there, because data cached before the server sent it has none.
- `getIssueTypeKind`, `isSystemManagedKind`, `isSystemManagedType`, `isEpicKind` (they fall back to `is_epic` when `kind` is missing): `packages/utils/src/work-item/type-kind.ts`.
- Which types a select or a type list offers: `apps/web/helpers/issue-type-options.ts`.
- The mark of a type: `getWorkItemTypeMarkKind` (`apps/web/helpers/work-item-type-mark.ts`) and `WorkItemTypeMarkIcon` (`apps/web/components/issues/issue-details/issue-identifier.tsx`).

- `IssueTypeKind`, `ISSUE_TYPE_KIND_LEVELS`, `SYSTEM_MANAGED_ISSUE_TYPE_KINDS`, `PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS`: `apps/api/plane/db/models/issue_type.py`.
- `ensure_project_kind_type(project, kind)`, `issue_type_assignment_error(...)`, `refuse_system_managed_type(issue_type, action)` (the shared guard of the endpoints above): `apps/api/plane/utils/project_issue_types.py`.
- The catalogue: `apps/api/plane/utils/issue_type_catalogue.py`. The milestone date rule: `apply_milestone_dates` (`apps/api/plane/utils/milestone_dates.py`) and `getMilestoneDateChange` (`packages/utils/src/work-item/dates.ts`), which the web app uses to preview it.
- `parent_kind_error(child_kind, parent_kind)`, `validate_work_item_parent(...)`: `apps/api/plane/utils/work_item_hierarchy.py`.
- `Issue.progress_objects`, `not_epic_q(prefix)`: progress numbers without Epics and reviews (`apps/api/plane/utils/epic_progress.py`).
