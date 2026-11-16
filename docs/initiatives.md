# Initiatives and goals

An **initiative** is a body of work that spans projects. A **goal** states an outcome that initiatives work toward. Both belong to the workspace, not to a project.

This page describes the model and the API. The pages in the app come later; nothing in the app uses these endpoints yet.

## Model

One model with two levels (`kind`):

- A **goal** has no parent and no projects of its own. Its progress is the progress of its initiatives.
- An **initiative** can have a goal as its parent, but does not need one. Projects and Epics are linked to initiatives. A project can belong to several initiatives.

| Field                               | Notes                                                                       |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `kind`                              | `goal` or `initiative` (the default). Cannot be changed after creation.     |
| `parent`                            | A goal of the same workspace. Only for an initiative.                       |
| `name`                              | Required.                                                                   |
| `description`, `description_html`   | Plain text and rich text. The HTML is sanitised like other descriptions.    |
| `lead`                              | An active member of the workspace.                                          |
| `start_date`, `target_date`         | The target date cannot be before the start date.                            |
| `status`                            | `planned` (default), `active`, `paused`, `completed`, `cancelled`.          |
| `health`                            | `on_track`, `at_risk`, `off_track`, or empty when nobody has judged it yet. |
| `logo_props`, `color`, `sort_order` | Presentation. A new one goes to the end of the list.                        |

Linked to an initiative:

- **Projects** (`InitiativeProject`): each project once per initiative.
- **Epics** (`InitiativeEpic`): work items whose type is an Epic. An Epic can be linked without its project.
- **Updates** (`InitiativeUpdate`): status notes with an author, a health and a text. Goals have updates too.

Deleting a goal keeps its initiatives; they lose their goal. Deleting an initiative removes its links and updates, never the projects or Epics.

## Who can do what

- Workspace **admins and members** read and manage initiatives, links and updates.
- **Guests** have no access (403). A guest sees a narrowed part of single projects, and an initiative shows numbers across projects.
- A person can link and unlink only **projects they are a member of**, and Epics in such projects.

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
  "initiative_ids": []
}
```

- The numbers are the work items of the linked projects by state group. Epics are not counted, so an Epic is not counted next to its own children. Archived work items, drafts and triage are left out, as in module and cycle progress.
- A **goal** counts the projects of all its initiatives. A project that is in two initiatives of one goal is counted once. `initiative_ids` lists the initiatives of a goal; `project_ids` of a goal are the projects of its initiatives.
- Only projects the person is an **active member** of are counted and listed. The others are left out of `progress` and `project_ids`; `hidden_project_count` says how many there are and `progress_is_partial` is `true`. Their ids, names and sizes are never returned. This holds for workspace admins too: a number is shown only to people who can open the project.
- Linked Epics follow the same rule: `epic_ids` has the Epics in projects the person is a member of, `hidden_epic_count` the rest.

The list endpoint uses a fixed number of queries, whatever the number of initiatives.

## API

All under `/api/workspaces/<slug>/initiatives/` (session API of the app).

| Method and path                       | What it does                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `GET /`                               | List. Filters: `kind`, `status` (comma separated), `parent` (a goal id, or `none`), `project` (a project id). |
| `POST /`                              | Create. `name` is required.                                                                                   |
| `GET /<id>/`                          | One initiative or goal with progress.                                                                         |
| `PATCH /<id>/`                        | Change fields. `kind` cannot be changed.                                                                      |
| `DELETE /<id>/`                       | Delete.                                                                                                       |
| `POST /<id>/projects/`                | Link projects: `{"project_ids": [...]}`. Projects already linked are skipped. Returns the initiative.         |
| `DELETE /<id>/projects/<project_id>/` | Unlink a project.                                                                                             |
| `POST /<id>/epics/`                   | Link Epics: `{"epic_ids": [...]}`. Returns the initiative.                                                    |
| `DELETE /<id>/epics/<epic_id>/`       | Unlink an Epic.                                                                                               |
| `GET /<id>/updates/`                  | Status updates, newest first.                                                                                 |
| `POST /<id>/updates/`                 | Add an update: `{"health": "at_risk", "text": "..."}`. The health becomes the health of the initiative.       |

Notes:

- The `project` filter returns nothing for a project the person is not a member of, so it cannot be used to find out where a project is linked.
- Linking answers 400 with one message for a project of another workspace, an unknown id, and a project the person is not in. Nothing is linked when one id in the list is refused.
- Unlinking a project or an Epic the person cannot see answers 404, like a link that does not exist.
