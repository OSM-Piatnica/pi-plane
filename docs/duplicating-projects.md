<!--
Copyright (c) 2026-present Maciej Szymczak and contributors
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
Adapted from the project duplication docs of Hangar (szymczag/hangar, AGPL-3.0-only).
See the LICENSE file for details.
-->

# Duplicating a project

Pi-Plane can copy a project's **configuration** into a new project, so a project
that is set up the way your team works can be used as a template. Use
**Duplicate project** in a project card's menu or in the project's general
settings. There is no feature flag and nothing to configure.

## What a copy contains

| Always copied                                                                                                   | Copied unless you opt out         | Copied only if you opt in                  | Never copied                                                        |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------ | ------------------------------------------------------------------- |
| Project settings, feature toggles (cycles, modules, pages, intake, time tracking, work item types), cover image | Labels, including their hierarchy | Members and their roles                    | Pages                                                               |
| States, including the triage state                                                                              | Estimates and their points        | Cycles, as empty shells                    | Webhooks and workflows                                              |
| Links to the work item types the source uses                                                                    | Intake configuration              | Modules, as empty shells, with their links | Published boards, favourites, drafts, notifications, import history |
|                                                                                                                 |                                   | Views, subject to the privacy rules below  | Comments, attachments, activity, time entries and subscribers       |
|                                                                                                                 |                                   | **Work items**, in the background          |                                                                     |

The copy always gets a **new name and identifier**, and the person who made it
becomes its project lead and an admin.

### Why some things are not copied

- **Work items, by default.** A template is a shape, not a backlog. They are opt-in; see below.
- **Webhooks.** A copied webhook would start posting a new project's events to
  an endpoint whose owner never asked for them.
- **Members, by default.** Copying membership grants people access to something
  they have not asked for. When you opt in, everyone the copy adds is emailed,
  exactly as if you had added them by hand, and each person's role is capped to
  their workspace role (reported as `members:role-adjusted`). Anyone who has
  left the workspace is skipped (`members:not-in-workspace`).
- **Someone else's private views** are skipped (`views:private`).
- **A lead or default assignee who is not in the copy** is dropped rather than
  left pointing at somebody with no access.

Anything skipped is listed in the response's `copy_summary.skipped`.

### Reset rather than carried over

- `external_source` and `external_id` are cleared everywhere: they identify rows
  that came from an import, and a copy is not the same row.
- Cycle progress snapshots, archive timestamps and lock flags start empty.
- Saved view filters are translated into the copy's own states and labels;
  anything with no counterpart is dropped (`views:unmapped-filters`).

## Who can do it

Both are required:

1. **On the source project**: an active **admin**. Workspace admins are not
   exempt: an admin who is not a member of the project cannot copy it, which
   stops a Secret project being copied by someone who cannot open it. Admin is
   required rather than member because the copy re-links the source's work item
   types, which are shared definitions.
2. **In the workspace**: admin or member, the same bar as creating a project.

## Copying the work items

Tick **Work items** in the form and the new project is created at once, empty; its work items follow in
the background and a bar at the top of the project shows the progress. When the copy finishes you are
offered a reload. A failed copy (for example after a restart) is retried automatically a few times; if it
still fails, an admin of the project gets a **Retry** button, and a retry carries on from where it stopped.

Which work items: everything in the project except **drafts, archived items and intake (triage) items**.
Work item numbers are kept (`ABC-12` is `ABC-12` in the copy), as are the original author and the created
and updated dates. Nothing is copied twice: a retry only adds what is missing.

Which parts of them are carried is chosen in the form, in groups, each switched on or off singly or through
its group (everything is on by default):

| Group                   | Options                                                                      |
| ----------------------- | ---------------------------------------------------------------------------- |
| Content                 | dates (start, due, duration), custom property values, images in descriptions |
| People                  | assignees (only people who are in the copy)                                  |
| Organization            | labels, cycle membership, module membership                                  |
| Hierarchy and relations | sub-work-item links, relations (both ends must be in the copy), links        |

Cycle and module membership is only carried when the cycles and modules themselves are copied. Custom
property values naming people who are not in the copy lose those people. Images in descriptions are
copied as files of their own, so deleting either project leaves the other's images alone; an image that
cannot be copied is removed from the description rather than left pointing at the source.

Only one work item copy runs per workspace at a time (a second is refused with `409`), and a project with
more than 20,000 work items is refused with `PROJECT_TOO_LARGE_TO_COPY`.

## The API

```
POST /api/workspaces/<slug>/projects/<project_id>/duplicate/
```

Every field is optional.

```jsonc
{
  "name": "Marketing (Copy)", // omitted: "<name> (Copy)", then "(Copy 2)" ...
  "identifier": "MKTG2", // omitted: derived from the source's identifier
  "network": 0, // omitted: inherits the source's visibility
  "include": {
    "labels": true, // default true
    "estimates": true, // default true
    "intake": true, // default true
    "members": false, // default false
    "cycles": false, // default false
    "modules": false, // default false
    "views": false, // default false
    "work_items": false, // default false; copied in the background
  },
  "work_item_properties": ["dates", "labels"], // only with work_items; omitted: all of them
}
```

`states` and `work_item_types` are always copied. An unrecognised key in
`include`, or an unknown name in `work_item_properties`, is rejected. The properties are `dates`,
`custom_properties`, `description_images`, `assignees`, `labels`, `cycles`, `modules`, `parents`,
`relations` and `links`. On success the response is the created project, in the
shape project creation returns, plus `copy_summary` (`source_project_id`,
`counts`, `skipped`, and `work_items` with the job's id, status and total when work items were asked for).

The progress of the background copy is read from the new project:

```
GET  /api/workspaces/<slug>/projects/<new_project_id>/copy-status/   // { "job": {status, copied, total, ...} } or { "job": null }
POST /api/workspaces/<slug>/projects/<new_project_id>/copy-retry/    // admin; only for a failed copy
```

| Status | `error`                                   | Meaning                                               |
| ------ | ----------------------------------------- | ----------------------------------------------------- |
| 400    | `PROJECT_NAME_ALREADY_EXIST`              | The name you supplied is taken in this workspace      |
| 400    | `PROJECT_IDENTIFIER_ALREADY_EXIST`        | The identifier you supplied is taken                  |
| 400    | `PROJECT_ARCHIVED`                        | The source project is archived; restore it first      |
| 400    | `PROJECT_TOO_LARGE_TO_COPY_SYNCHRONOUSLY` | Over a size limit, see below                          |
| 403    | -                                         | Not an admin of the source, or cannot create projects |
| 404    | -                                         | No such project in this workspace                     |
| 429    | -                                         | Rate limited                                          |

## Limits

A copy runs in one database transaction inside the request, so it is atomic. It
is refused above 200 members, 500 cycles and modules combined, or 5000 rows in
total, because past those the transaction holds the workspace lock long enough
to delay other people creating projects.

Duplication is rate limited per user (`PROJECT_DUPLICATE_USER_RATE`, default
`10/hour`) and per workspace (`PROJECT_DUPLICATE_WORKSPACE_RATE`, default
`30/hour`).

## The cover image

The copy gets its own copy of the source's cover file, made after the database
transaction commits. A cover that cannot be copied does not fail the project:
the copy is created without one and the response says `cover_image:failed` (or
`cover_image:unreadable`).

## Known limitations

- **Pages are not copied.** Use the duplicate action on a page.
- **Cycles and modules arrive empty** unless the work items are copied too.
- **Workflows are not copied.**
