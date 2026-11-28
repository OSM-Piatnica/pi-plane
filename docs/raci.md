<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# RACI on work items

A work item can say which [departments](departments.md) answer for it and in what way. Each department has at
most one role on a work item:

| Role        | English letter | Polish letter  | Meaning                          |
| ----------- | -------------- | -------------- | -------------------------------- |
| Responsible | R              | O (Odpowiada)  | does the work and keeps the date |
| Approver    | A              | Z (Zatwierdza) | accepts or rejects the result    |
| Consulted   | C              | K              | gives input before the decision  |
| Informed    | I              | I              | hears about the result           |

Several departments may share a role, "responsible" included: two responsible departments answer for the work
item together. The roles are stored by these neutral names; the letters are a matter of the language of the
interface (Polish shows O / Z / K / I, English and the other languages R / A / C / I). Pickers and tooltips show
the full name of the role.

## Switching it on

RACI is off until it is switched on in two places:

1. **The workspace**: Settings → Features → RACI (workspace admins). See [workspace-features.md](workspace-features.md).
2. **The project**: project settings → Features → RACI (project admins).

While either is off, nothing about RACI is shown and the API refuses the RACI endpoint of the work item; the
roles already given are kept and come back when it is switched on again.

## Who may change the roles

The admins of the project and its lead. Everybody who can see a work item can see its roles; a guest who only
sees the work items they created only sees the roles of those.

## Where the roles show

- **Work item detail and peek view**: a RACI section lists the active departments of the workspace, each with a
  picker of none and the four roles. It is read only for people who may not change the roles.
- **Lists and spreadsheet**: the display properties "Responsible", "Approver" and "Consulted" show the
  departments with that role as chips of the department's code and colour (the name when it has no code), and
  the spreadsheet has a column for each.
- **Timeline**: Display → Color by → Responsible department colours a bar with the colour of the responsible
  department; with several responsible departments the bar is split into equal stripes, one per department. A
  work item without a responsible department, or whose departments have no colour, keeps its state colour.
- **Activity**: every role that is given, changed or taken away is recorded with the department and the role.
- **Filters**: "Department (any role)" and one filter per role. Each takes departments and **My department**,
  the department the person who filters is in (the active department group they belong to). Like the other
  filters they find sub-work items too, as long as the sub-work items are shown in the list.

## Departments that change

- A department that is **switched off** keeps its roles, and they are still shown. It is not offered for new
  roles, and its role cannot be changed, only taken away.
- A department that is **deleted**, or turned back into a plain group, loses its roles on every work item.
- A person with no department finds nothing with "My department".

## Copying a project

[Duplicating a project](duplicating-projects.md) copies the RACI switch with the other feature toggles, and,
when the work items are copied, their roles (option "RACI roles" in the "People" group). Departments belong to
the workspace, so the copy names the same departments.

## Import and export

**Export work items** (workspace settings → Exports) writes a column **RACI** (in the "People" group of
columns), one cell per work item, for example `O:RM;O:PR;Z:ZA;K:KS`:

- each entry is a letter, a colon and a department; entries are separated by `;`;
- the department is its code, or its name when it has no code; a `;` inside a name is written `\;`;
- the letters are those of the language of the person who exports: O / Z / K / I in Polish, R / A / C / I in
  the other languages; roles come in the order responsible, approver, consulted, informed;
- the cell is empty for a project (or a workspace) with RACI off.

**Import work items** (workspace settings → Imports) reads the same column, with Polish or English letters
(both mean the same roles; I is "informed" in both), in upper or lower case. Labels of the form `O:RM`, as the
Gantt-RACI prototype keeps roles, become roles too, instead of labels. Option "RACI roles" in "What to import"
leaves all of it out. A department is found by its code, then by its name.

Roles come in only when the target project has RACI on (workspace and project) and the person importing may
change roles (an admin or the lead of the project). Otherwise the work items are imported without roles, one
warning says why, and `O:XX` labels stay labels. The import reports and skips:

- an entry that is not a letter, a colon and a department;
- a department that is not known (a label that names no department stays a label instead);
- a name shared by several departments (use the code);
- a department that is switched off (it cannot be given a role, as in the app);
- a second role for the same department on one work item (the RACI column comes before labels, and the first
  role wins).

An import writes no activity entries for the roles, as it writes none for labels or modules.

## API

- `GET /api/workspaces/<slug>/projects/<project_id>/issues/<issue_id>/raci/` answers
  `{"raci": [{"group_id": "<department id>", "role": "responsible"}, ...], "can_edit": true}`.
- `PUT` on the same address with `{"raci": [...]}` replaces every role of the work item in one call: a
  department that is left out loses its role, and an empty list clears the work item. Each entry needs a
  department of the workspace (a user group of kind `department`) and one of `responsible`, `approver`,
  `consulted`, `informed`; a department may appear once. `400` when RACI is off or the list is not valid, `403`
  for people who may not change it.
- Work item lists and the work item detail carry `raci` in the same shape (an empty list where RACI is off),
  read with one subquery per list.
- Filters (`filters` of the work item lists): `raci_department_id` / `raci_department_id__in` for any role and
  `raci_responsible_id`, `raci_approver_id`, `raci_consulted_id`, `raci_informed_id` (each also with `__in`).
  The values are department ids and `my_department`.
- `GET /api/workspaces/<slug>/departments/?include_inactive=true` lists the switched-off departments too, so
  that their roles can be shown.
- `GET /api/workspaces/<slug>/raci-notifications/` (any member) answers
  `{"events": [...], "matrix": {"comment": ["responsible", "consulted"], ...}, "defaults": {...}}`; `PATCH` with
  `{"matrix": {"<event>": [roles]}}` (workspace admins) changes the events given and keeps the others.
- `GET .../issues/<issue_id>/raci/notifications/` answers, per event, the roles it reaches, the departments of
  the work item with one of them (`group_id`, `role`, `member_count`) and `member_ids`, the people RACI adds.
- `GET /api/workspaces/<slug>/projects/<project_id>/raci-warnings/` (project admins and members) answers
  `counts` per kind, `items` per kind (at most `max_listed`, 200, each `id`, `name`, `sequence_id`) and
  `departments` (`group_id`, `is_active`, `member_count`, `project_member_count`, `reason`).

## Notifications by role

When something happens on a work item, the people of the departments with a role on it hear about it, if the
workspace's notification matrix ticks that role for the event. The matrix is in Settings → Departments, below the
list of departments (workspace admins), shown while the workspace has RACI on. Its defaults are the table of
SPEC-02:

| Event                           | What sends it                                     | R   | A   | C   | I   |
| ------------------------------- | ------------------------------------------------- | --- | --- | --- | --- |
| New draft version or attachment | an attachment is added                            | ✓   |     | ✓   |     |
| Comment                         | a comment is added                                | ✓   |     | ✓   |     |
| Approval requested              | acceptance (workstream C), not sent yet           | ✓   | ✓   |     |     |
| Approved or rejected            | acceptance (workstream C), not sent yet           | ✓   | ✓   | ✓   |     |
| Final version (completed)       | the state moves to a state of the completed group | ✓   | ✓   | ✓   | ✓   |
| State or due date changed       | the state or the due date (`target_date`) changes | ✓   |     | ✓   | ✓   |

- A move to a completed state is both "Final version" and "State or due date changed": whoever either of them
  reaches hears about it, once.
- Other changes (name, priority, planned dates, ...) reach subscribers and assignees only, as before.
- The people of a department are its direct members while it is switched on; a switched-off department tells
  nobody. A person in several departments hears when any of them qualifies, so this does not depend on
  [#508](https://github.com/OSM-Piatnica/pi-plane/issues/508).
- Only active members of the project are told, never the person who made the change, and nobody twice:
  subscribers, assignees and mentioned people get their notification as before. In-app notifications from RACI
  have the sender `in_app:issue_activities:raci`; email follows each person's notification preferences and the
  usual digest.
- Nothing is sent while RACI is off for the workspace or the project.

**Who will be notified**: the RACI section of the work item detail has a folded list "Who will be notified" that
shows, per event, the departments whose role it reaches and how many people that makes (in red when none).

Acceptance will send its own two events through `raci_recipient_ids(issue, event)` in
`apps/api/plane/utils/raci_notifications.py`.

## Warnings

The work items header of a project with RACI on has a button "RACI warnings" with their number (for project
admins and members, and only when there is something to warn about). It opens the list, each work item a link to
it. Warnings never block a save. They look at open work items only (not completed, cancelled, archived, drafts or
in triage), and not at the review steps of an acceptance:

- **Work items without a responsible department**, sub-work items included.
- **Milestones without an approver**: work items of a type of kind milestone.
- **Departments whose notifications reach nobody**: a department with a role on an open work item that is switched
  off, has no members, or has none of them in the project.
- **Work items without a predecessor**: top-level work items that no timeline relation (blocked by, start before,
  finish before, start before finish; in any project) makes wait for another, except those that start the project
  (the earliest start date among the open top-level work items).
- **Work items nothing depends on**: top-level work items that are nobody's predecessor, except those with a due
  date and those that end the project (the latest planned finish).

The two dependency warnings are given only in a project that has at least one timeline relation; without any,
every work item would be listed.

## Not there yet

- The work items one's departments approve are listed by the [focus endpoint](focus.md) (D9); its "My view" panel is
  still to come.
- One department per person is the rule of [#508](https://github.com/OSM-Piatnica/pi-plane/issues/508) for now.
  "My department" and the notifications already take every active department group a person belongs to, so they
  keep working if that rule changes.
