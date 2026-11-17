# Work item types and kinds

A work item type has two sides:

- **Kind**: what the system does with work items of the type. A fixed list, set by code. Users cannot edit it.
- **Everything else**: name, icon, description, custom properties, the projects that use the type. Editable in **Workspace settings → Work item types**. "Bug", "Story" and "Change request" are ordinary types of the `standard` kind that differ only in these.

## Kinds

| Kind | Level | Behaviour |
|---|---|---|
| `standard` | 0 | No special behaviour. A workspace can have any number of these. |
| `epic` | 1 | Groups other work items: no parent, left out of module and cycle progress. See [Epics](epics.md). |
| `milestone` | 0 | Reserved for milestones (one date, a diamond on the timeline). Hierarchy rules apply now; the rest comes later. |
| `approval` | 0 | Reserved for acceptance work items. System-managed. |
| `review` | -1 | One step of an approval: only as a child of an `approval` work item. System-managed. |

A work item without a type behaves like the `standard` kind.

## Rules that follow from the kind

**Hierarchy.** Checked by the server for the app, the public API, the sub-work item endpoint and the work item import:

- an `epic` has no parent;
- a `review` must have an `approval` parent, so it cannot be created without one, moved elsewhere or detached;
- a child's level is never above its parent's level, so a `review` has no children.

| Parent ↓ / Child → | standard | epic | milestone | approval | review |
|---|---|---|---|---|---|
| standard | yes | no | yes | yes | no |
| epic | yes | no | yes | yes | no |
| milestone | yes | no | yes | yes | no |
| approval | yes | no | yes | yes | yes |
| review | no | no | no | no | no |

**System-managed kinds** (`approval`, `review`). The type of an existing work item cannot be changed into or out of these kinds; taking the type off (`type_id: null`) counts as a change out of the kind. The API answers `400` with `{"error": "...", "error_code": "WORK_ITEM_TYPE_SYSTEM_MANAGED"}`. A new work item can be created with such a type. The work item import does not assign these types: the row comes in without a type, with a warning.

**Progress.** `epic` and `review` work items are left out of the progress numbers of modules and cycles: an Epic is counted through its children, and an acceptance counts once, through its `approval` work item. They still show in the lists.

## `kind` and `is_epic`

`is_epic` is the older flag for the Epic kind. Upstream code and the public API read it, so it stays, and it is always equal to `kind == "epic"`:

- the model keeps the two in step when a type is saved; a changed `kind` decides, otherwise `is_epic` moves a type between `standard` and `epic`;
- a database check constraint (`issue_type_is_epic_matches_kind`) refuses a write that sets only one of them, which covers code that skips `save()` (`QuerySet.update`, `bulk_create`, `bulk_update`). Such code has to write both fields.

The type endpoints return `kind` as a read-only field. The type form can still switch `is_epic` on a `standard` or `epic` type that no work item uses; it is refused on the other kinds.

## System types

`epic`, `milestone`, `approval` and `review` each have one type per workspace that the system uses: the oldest active type of the kind, created on demand under the name of the kind (it can be renamed afterwards) and linked to the project that needs it. Creation takes turns per workspace (a lock on the workspace row), so two requests at the same moment end up with one type. There is no unique constraint: admins can still make more types of the Epic kind. For Epics this is the **Epics** switch in the project's feature settings; the other kinds are linked by the features that use them.

## For developers

- `IssueTypeKind`, `ISSUE_TYPE_KIND_LEVELS`, `SYSTEM_MANAGED_ISSUE_TYPE_KINDS`, `PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS`: `apps/api/plane/db/models/issue_type.py`.
- `ensure_project_kind_type(project, kind)`, `issue_type_assignment_error(...)`: `apps/api/plane/utils/project_issue_types.py`.
- `parent_kind_error(child_kind, parent_kind)`, `validate_work_item_parent(...)`: `apps/api/plane/utils/work_item_hierarchy.py`.
- `Issue.progress_objects`, `not_epic_q(prefix)`: progress numbers without Epics and reviews (`apps/api/plane/utils/epic_progress.py`).
