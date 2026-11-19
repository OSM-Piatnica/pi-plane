# Departments

A workspace can keep a list of the departments of the organisation, and every person has at most one department in the workspace. Later features (RACI on work items, "my department" filters, notifications by role) build on it.

Open **Settings → Departments** in the workspace. Only workspace admins see this page.

## Departments are user groups

A department is a [user group](user-groups.md) of the kind _department_. There is one list of the organisation's units, not two: a department has members, can be nested, can be assigned work items and can be a member of a project, like any other group. On top of what a group has, a department has:

- a **code**: a short label such as `RM`, stored in upper case. Two departments of a workspace cannot have the same code; a department may have none.
- a **colour**: a hex colour, or none.
- a **place** in the list. The arrows on the settings page move a department up and down; pickers show the departments in this order.
- a switch. A department that is **switched off** stays on the people who have it, and is no longer offered to choose.

Only workspace admins add departments and change the code, the colour, the place, the switch or the kind of a group. Departments also appear on the Groups page. Unlike other groups, a department is managed by workspace admins only: a group admin of a department cannot change its members, rename it, move it, delete it or create subgroups under it. Ordinary groups nested below a department stay with their own group admins.

### Import from a list

**Import list** takes a pasted list with one department per line, as `CODE;Name` (a tab works as the separator too, so two columns can be copied from a spreadsheet). A line without a separator is a department without a code. Departments whose code or name is already there are left out, and the dialog shows how many will be added and which lines cannot be used before anything is created.

```
RM;Marketing
QA;Quality
IT;IT services
```

## The department of a person

- Only workspace admins set departments, their own included, in **Settings → Members**, in the **Department** column. Members and guests cannot choose their department: a department's group can be a member of projects, so choosing one would let anyone into those projects. The column appears once the workspace has a department; members see it read-only, guests do not see it.
- A workspace admin who has no department is asked for their own when they open the workspace, as soon as the workspace has at least one department to choose from. The question can be put off with **Later**; it comes back in the next browser session.

### How the department and the group membership go together

A person's department is always a group they belong to:

- Giving a person a department puts them in that group (as a plain member). Changing it, or taking it away, takes them out of the previous department's group, but only when that membership was made by giving the department and is still a plain one: a membership added by hand on the Groups page, or one where the person has since been made a group admin, stays.
- Taking a person out of the group (on the Groups page) clears their department when it was that one.
- Putting a person who has no department into a department's group makes it their department. A person who already has one keeps it: they may belong to further department groups, and only the one set on them counts as theirs.
- Turning a plain group into a department gives it as department to those of its direct members who have none.
- Deleting a department, or turning it back into a plain group, leaves its people without a department. They stay in the workspace.

### Departments from the identity provider

Groups mirrored from the identity provider (see [Groups managed outside](user-groups.md#groups-managed-outside)) can be departments too, for example the groups made from the Entra _department_ attribute. A mirrored group does not become a department by itself: a workspace admin turns it into one (through the API, `PATCH .../user-groups/<id>/` with `{"kind": "department"}`; code and colour can then be set on the Departments page). After that:

- at each sign-in, a person the provider puts in that group and who has no department gets it as their department;
- a person who leaves the group at the provider loses the department;
- such a department can be given by hand only to a person the provider already put in it, because the provider decides who belongs to it;
- a department that comes from the provider cannot be changed or cleared in Plane, only at the provider; a person moved to another department at the provider gets the new one at their next sign-in;
- a department a workspace admin gave by hand is never replaced by the sign-in.

## API

- `GET /api/workspaces/<slug>/user-groups/?kind=department` lists the departments (in their order); `kind=group` lists the other groups. Create and change take `kind`, `code`, `color`, `sort_order` and `is_active` (workspace admins only).
- `GET /api/workspaces/<slug>/departments/` lists the departments that are switched on, open to every member of the workspace, guests included.
- `PATCH /api/workspaces/<slug>/members/<workspace member id>/department/` with `{"department": "<group id>"}` or `{"department": null}` sets a person's department (workspace admins only).
- The workspace members list and `workspace-members/me/` carry `department` (the id of the group).

## Not there yet

- RACI roles on work items, filters and notifications by department come with later changes.
