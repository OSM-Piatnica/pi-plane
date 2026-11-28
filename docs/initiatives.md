# Initiatives and goals

An **initiative** is a body of work that spans projects. A **goal** states an outcome that initiatives work toward. Both belong to the workspace, not to a project.

This page describes the model, the API and the Initiatives app of the web client.

The feature is switched off in a new workspace. A workspace admin switches it on in workspace settings, "Features" (see [`workspace-features.md`](./workspace-features.md)). While it is off, every endpoint below answers 403 to everybody, admins included, and the app is not in the rail.

## Model

One model with two levels (`kind`):

- A **goal** has no parent and no projects of its own. Its progress is the progress of its initiatives.
- An **initiative** can have a goal as its parent, but does not need one. Projects and Epics are linked to initiatives. A project can belong to several initiatives.

| Field                               | Notes                                                                                                                   |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `kind`                              | `goal` or `initiative` (the default). Cannot be changed after creation.                                                 |
| `parent`                            | A goal of the same workspace. Only for an initiative.                                                                   |
| `name`                              | Required.                                                                                                               |
| `description`, `description_html`   | Plain text and rich text. The HTML is sanitised like other descriptions.                                                |
| `lead`                              | An active member of the workspace.                                                                                      |
| `start_date`, `target_date`         | The target date cannot be before the start date.                                                                        |
| `status`                            | `planned` (default), `active`, `paused`, `completed`, `cancelled`.                                                      |
| `health`                            | `on_track`, `at_risk`, `off_track`, or empty when nobody has judged it yet. Read only: set by the newest status update. |
| `logo_props`, `color`, `sort_order` | Presentation. A new one goes to the end of the list.                                                                    |

Linked to an initiative:

- **Projects** (`InitiativeProject`): each project once per initiative.
- **Epics** (`InitiativeEpic`): work items whose type is an Epic. An Epic can be linked without its project. Epics are not linked to a goal directly; a goal shows the Epics of its initiatives.
- **Updates** (`InitiativeUpdate`): status notes with an author, a health and a text. Goals have updates too.

Deleting a goal keeps its initiatives; they lose their goal. Deleting an initiative removes its links and updates, never the projects or Epics.

## Who can do what

In the workspace:

- Workspace **admins and members** read initiatives and goals, create and edit them, and write updates.
- **Deleting** one is for a workspace admin, its lead and the person who created it. Other members get 403.
- Workspace **guests** have no access (403). A guest sees a narrowed part of single projects, and an initiative shows numbers across projects.

Per project:

| The person                                                            | Sees its numbers and Epics | Links and unlinks it |
| --------------------------------------------------------------------- | -------------------------- | -------------------- |
| Workspace admin, member of the project or not                         | yes                        | yes                  |
| Member or admin of the project                                        | yes                        | yes                  |
| Guest of a project that shows everything to guests                    | yes                        | no (403)             |
| Guest of a project where guests see only the work items they created  | no (counted as hidden)     | no                   |
| Workspace member who is not in the project, or no longer active in it | no (counted as hidden)     | no                   |

A workspace admin sees and links every project of the workspace, so nothing is hidden from them. For everybody else the rules of the rest of the app apply: the numbers of a project are for the people who can see all its work items, and linking takes the Member role in the project.

## Progress

Every initiative in a list or detail response carries the progress for the person who asks:

```json
{
  "progress": { "total_issues": 6, "backlog": 1, "unstarted": 0, "started": 2, "completed": 3, "cancelled": 0 },
  "progress_is_partial": false,
  "hidden_project_count": 0,
  "project_ids": ["…"],
  "epic_ids": ["…"],
  "hidden_epic_count": 0,
  "initiative_ids": [],
  "epic_progress": { "total_issues": 4, "backlog": 0, "unstarted": 0, "started": 1, "completed": 3, "cancelled": 0 },
  "epic_progress_is_partial": false
}
```

- The numbers are the work items of the linked projects by state group. Epics are not counted, so an Epic is not counted next to its own children. Archived work items, drafts and triage are left out, as in module and cycle progress.
- A **goal** has the projects and the Epics of all its initiatives, each once: a project or an Epic that is in two initiatives of one goal is counted and listed once. `initiative_ids` lists the initiatives of a goal.
- Only projects whose numbers the person may see (the table above) are counted and listed. The others are left out of `progress` and `project_ids`; `hidden_project_count` says how many there are and `progress_is_partial` is `true`. Their ids, names and sizes are never returned.
- Linked Epics follow the same rule, on initiatives and on goals: `epic_ids` has the Epics in projects the person may see, `hidden_epic_count` the number of the others.
- Linked Epics do not add to `progress`. They have their own figure, `epic_progress` (below).

### The Epic figure

`epic_progress` counts the child work items of the linked Epics, by state group, apart from `progress`. It serves an initiative that owns one Epic of a larger shared project without owning the whole project.

- The children are the direct children of each Epic, counted like `progress`: no Epics (an Epic under an Epic is not counted), no reviews, no archived work items, drafts or triage.
- Only the Epics in `epic_ids` count. A goal counts the Epics of its initiatives, each once.
- An Epic the person may not see is not counted (it is in `hidden_epic_count`), and neither is a child in a project the person may not see. `epic_progress_is_partial` is `true` in both cases.
- The two figures are not added up: an Epic inside a linked project has its children in both, once in each.

What stays linked but is not shown:

- An **archived project** stays linked and stays in `project_ids`. Its work items do not count while it is archived. An archived project cannot be linked.
- An **archived Epic**, an Epic of an archived project and a work item that is **no longer an Epic** (its type was changed) are left out of `epic_ids` and of `hidden_epic_count`. The link stays and can be removed; an archived Epic shows again when it is restored.

The list endpoint uses a fixed number of queries, whatever the number of initiatives. It is not paginated.

## API

All under `/api/workspaces/<slug>/initiatives/` (session API of the app).

| Method and path                       | What it does                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `GET /`                               | List. Filters: `kind`, `status` (comma separated), `parent` (a goal id, or `none`), `project` (a project id). |
| `POST /`                              | Create. `name` is required.                                                                                   |
| `GET /<id>/`                          | One initiative or goal with progress.                                                                         |
| `PATCH /<id>/`                        | Change fields. `kind` cannot be changed; `health` is ignored (it comes from status updates).                  |
| `DELETE /<id>/`                       | Delete (workspace admin, lead or creator).                                                                    |
| `POST /<id>/projects/`                | Link projects: `{"project_ids": [...]}`. Projects already linked are skipped. Returns the initiative.         |
| `DELETE /<id>/projects/<project_id>/` | Unlink a project.                                                                                             |
| `GET /<id>/epics/`                    | The linked Epics the person may see (`epic_ids`), each with its own figure (below).                           |
| `POST /<id>/epics/`                   | Link Epics: `{"epic_ids": [...]}`. Returns the initiative.                                                    |
| `GET /<id>/epics/search/`             | Epics the person may link: `?search=` matches the name or the number (`12` or `ABC-12`). At most 20.          |
| `DELETE /<id>/epics/<epic_id>/`       | Unlink an Epic.                                                                                               |
| `GET /<id>/updates/`                  | Status updates, newest first.                                                                                 |
| `POST /<id>/updates/`                 | Add an update: `{"health": "at_risk", "text": "..."}`. The health becomes the health of the initiative.       |

Notes:

- One request links at most 100 projects or Epics.
- The `project` filter returns nothing for a project whose numbers the person may not see, so it cannot be used to find out where a project is linked.
- Linking answers 400 with one message for a project of another workspace, an unknown id, and a project the person cannot see. It answers 403 for a project they see but may not link. Nothing is linked when one id in the list is refused.
- Unlinking a project or an Epic the person cannot see answers 404, like a link that does not exist. Unlinking one they see but may not link answers 403.
- `GET /<id>/epics/` returns, per Epic: `id`, `name`, `sequence_id`, `project_id`, `project_identifier`, `state_id`, `state_group`, `target_date`, and `progress` with `progress_is_partial` for its children, counted as in the Epic figure.
- `GET /<id>/epics/search/` offers the Epics that are not archived, not linked to this initiative yet, and in a project the person may link. It answers 400 on a goal.
- Images in a description are uploaded as workspace assets of type `INITIATIVE_DESCRIPTION`, by workspace admins and members only.

## The app

The Initiatives app is a rail app (`/:workspaceSlug/initiatives`, see [`app-rail.md`](./app-rail.md)) for workspace admins and members, while the feature is switched on.

- **Sidebar:** all initiatives, then each goal with its initiatives (a goal can be folded), then the initiatives without a goal.
- **List:** the same grouping, with the progress of the linked projects, health, dates, status and lead. Status and dates can be changed in the row. "New goal" and "New initiative" create one and open it.
- **Detail:** name, description (the rich text editor), both progress figures with a note when they are partial, the initiatives of a goal, the linked projects and Epics, and status updates. The properties panel on the right (status, health, lead, dates, goal, creator) folds with the button in the header; the state is the theme store's `initiativesSidebarCollapsed`.
- **Links:** on an initiative, "Add projects" offers the projects the person may link, "Add Epic" searches the Epics they may link, and the unlink button shows only where they may unlink. The API decides; the web mirrors it with `canLinkInProject`. A goal shows the projects and Epics of its initiatives, read only.
- **Status updates:** a health and a text; the newest health becomes the health of the initiative. Health is only set through updates, in the app and in the API.
- **Delete** is in the header for a workspace admin, the lead and the creator (`canDeleteInitiative`).

Where things live: `apps/web/app/(all)/[workspaceSlug]/(initiatives)/` (routes, layout, sidebar), `apps/web/components/initiatives/`, `apps/web/store/initiative.store.ts`, `apps/web/services/initiative.service.ts`, `apps/web/helpers/initiatives.ts`, types in `packages/types/src/initiative.ts`, statuses and healths in `packages/constants/src/initiative.ts`, strings under `initiatives` in `pi-extensions.json`.
