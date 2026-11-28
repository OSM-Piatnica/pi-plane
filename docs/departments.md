# Departments

A workspace can keep a list of the departments of the organisation, and every person belongs to at most one department in the workspace. Later features (RACI on work items, "my department" filters, notifications by role) build on it.

Open **Settings → Departments** in the workspace. Only workspace admins see this page.

## Departments are user groups

A department is a [user group](user-groups.md) of the kind _department_. There is one list of the organisation's units, not two: a department has members, can be nested, can be assigned work items and can be a member of a project, like any other group. On top of what a group has, a department has:

- a **code**: a short label such as `RM`, stored in upper case. Two departments of a workspace cannot have the same code; a department may have none.
- a **colour**: a hex colour, or none.
- a **place** in the list. The arrows on the settings page move a department up and down; pickers show the departments in this order.
- a switch. A department that is **switched off** keeps its members, but is nobody's department and is left out of pickers.

Only workspace admins add departments and change the code, the colour, the place, the switch or the kind of a group. Departments also appear on the Groups page, where their members are managed. Unlike other groups, a department is managed by workspace admins only: a group admin of a department cannot change its members, rename it, move it, delete it or create subgroups under it.

### Import from a list

**Import list** takes a pasted list with one department per line, as `CODE;Name` (a tab works as the separator too, so two columns can be copied from a spreadsheet). A line without a separator is a department without a code. Departments whose code or name is already there are left out, and the dialog shows how many will be added and which lines cannot be used before anything is created.

```
RM;Marketing
QA;Quality
IT;IT services
```

## The department of a person

A person's department is the active department group they belong to. There is no separate department field on the person: who works in which department is who is in which department group.

- **One department per person.** A person belongs to at most one active department of a workspace. Adding someone to a department while they are in another one is refused, with the department they are already in; to move a person, take them out of the old department and add them to the new one. The same rule stops a group from being turned into a department, and a switched-off department from being switched on, while any of its members is in another active department (the error lists them).
- **Workspace admins assign departments**, on the **Groups** page, by adding people to the department's group (or the identity provider does, see below). Group admins of a department, members and guests cannot change who is in a department: a department's group can be a member of projects, so whoever could join it could get into those projects. Ordinary groups nested below a department stay with their own group admins, and belonging to such a group does not make the department a person's department.
- **Settings → Members** shows each person's department (code and name) once the workspace has a department. It is read only there; guests do not see the column.
- A department that is **switched off** keeps its members but is nobody's department until it is switched on again. Deleting a department, or turning it back into a plain group, leaves its people without a department. They stay in the workspace.

### Departments from the identity provider

Groups mirrored from the identity provider (see [Groups managed outside](user-groups.md#groups-managed-outside)) can be departments too, for example the groups made from the Entra _department_ attribute. A mirrored group does not become a department by itself: a workspace admin turns it into one (through the API, `PATCH .../user-groups/<id>/` with `{"kind": "department"}`; code and colour can then be set on the Departments page). The provider decides who is in it, as for any mirrored group. At each sign-in the one-department rule is applied like this:

- of the active departments the provider lists for the person, the **first one in the provider's list** is joined; the later ones are skipped (and a membership of them that an earlier sign-in made is taken out). The skip is logged;
- the provider's department wins over a department a workspace admin assigned by hand: that hand-made membership of another active department is taken out, and logged;
- when the provider gives the person no department, a department assigned by hand stays;
- memberships made by another identity provider are left to that provider.

## Why not a choice of one's own, or a field on the person

The first specification (SPEC-02) let people choose their own department, at onboarding or later, and kept the choice on the workspace member. Neither is done:

- **No self-choice.** A department is a group, and a group can be a member of projects. Letting people pick their department would let anyone join a group and, through it, get into its projects. Departments are assigned by workspace admins or by the identity provider instead.
- **No separate field.** A department field next to the group membership had to be kept in step with it on every path (adding and removing members, the sign-in sync, deleting or switching off a department) and could still disagree with it. The membership alone is the department.

## API

- `GET /api/workspaces/<slug>/user-groups/?kind=department` lists the departments (in their order); `kind=group` lists the other groups. Create and change take `kind`, `code`, `color`, `sort_order` and `is_active` (workspace admins only). A code is stored trimmed and in upper case and is checked for length after that; a code another department of the workspace has is refused with `409`, also when two requests race for it.
- `GET /api/workspaces/<slug>/departments/` lists the departments that are switched on, open to every member of the workspace, guests included.
- `GET /api/workspaces/<slug>/departments/members/` tells who works in which department, as `{"<user id>": "<department id>"}`, derived from the department groups. Read only. Guests only get their own department.
- People are added to and removed from a department with the group member endpoints (`POST /api/workspaces/<slug>/user-groups/<id>/members/`, `DELETE .../members/<user id>/`); a second active department is refused with `409`.

## Not there yet

- RACI roles of departments on work items and the "my department" filters: see [RACI on work items](raci.md). Notifications by department come with a later change.
