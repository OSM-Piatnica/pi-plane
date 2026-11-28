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

## Not there yet

- Notifications by role and the project warnings (a work item without a responsible department, and so on) come
  with D3 of the roadmap. The work items one's departments approve are listed by the [focus endpoint](focus.md) (D9);
  its "My view" panel is still to come.
- One department per person is the rule of [#508](https://github.com/OSM-Piatnica/pi-plane/issues/508) for now.
  "My department" already takes every active department group a person belongs to, so it keeps working if that
  rule changes.
