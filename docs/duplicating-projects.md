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

| Always copied                                                                                                   | Copied unless you opt out         | Copied only if you opt in                  | Never copied                                                                     |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------- |
| Project settings, feature toggles (cycles, modules, pages, intake, time tracking, work item types), cover image | Labels, including their hierarchy | Members and their roles                    | Work items and everything on them (comments, attachments, activity, subscribers) |
| States, including the triage state                                                                              | Estimates and their points        | Cycles, as empty shells                    | Pages                                                                            |
| Links to the work item types the source uses                                                                    | Intake configuration              | Modules, as empty shells, with their links | Webhooks and workflows                                                           |
|                                                                                                                 |                                   | Views, subject to the privacy rules below  | Published boards, favourites, drafts, notifications, import history              |

The copy always gets a **new name and identifier**, and the person who made it
becomes its project lead and an admin.

### Why some things are not copied

- **Work items.** A template is a shape, not a backlog.
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
  },
}
```

`states` and `work_item_types` are always copied. An unrecognised key in
`include` is rejected. On success the response is the created project, in the
shape project creation returns, plus `copy_summary` (`source_project_id`,
`counts`, `skipped`).

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
- **Cycles and modules arrive empty**, since there are no work items to put in
  them.
- **Workflows are not copied.**
