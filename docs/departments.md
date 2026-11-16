# Departments

A workspace can keep a list of the departments of the organisation, and every person has at most one department in the workspace. Later features (RACI on work items, "my department" filters, notifications by role) build on it.

Open **Settings → Departments** in the workspace. Only workspace admins see this page.

## Departments are user groups

A department is a [user group](user-groups.md) of the kind _department_. There is one list of the organisation's units, not two: a department has members, can be nested, can be assigned work items and can be a member of a project, like any other group. On top of what a group has, a department has:

- a **code**: a short label such as `RM`, stored in upper case. Two departments of a workspace cannot have the same code; a department may have none.
- a **colour**: a hex colour, or none.
- a **place** in the list. The arrows on the settings page move a department up and down; pickers show the departments in this order.
- a switch. A department that is **switched off** stays on the people who have it, and is no longer offered to choose.

Only workspace admins add departments and change the code, the colour, the place, the switch or the kind of a group. Departments also appear on the Groups page, where their members can be managed as for any group.

### Import from a list

**Import list** takes a pasted list with one department per line, as `CODE;Name` (a tab works as the separator too, so two columns can be copied from a spreadsheet). A line without a separator is a department without a code. Departments whose code or name is already there are left out, and the dialog shows how many will be added and which lines cannot be used before anything is created.

```
RM;Marketing
QA;Quality
IT;IT services
```

## The department of a person

- A workspace admin sets anyone's department in **Settings → Members**, in the **Department** column. Everybody else can set their own there. The column appears once the workspace has a department; guests do not see it.
- A member who has no department is asked for it when they open the workspace, as soon as the workspace has at least one department to choose from. The question can be put off with **Later**; it comes back in the next browser session. This is also what a person sees right after accepting an invitation or finishing onboarding.

### How the department and the group membership go together

A person's department is always a group they belong to:

- Choosing a department puts the person in that group (as a plain member). Changing it takes them out of the previous department's group; taking the department away does the same.
- Taking a person out of the group (on the Groups page) clears their department when it was that one.
- Putting a person who has no department into a department's group makes it their department. A person who already has one keeps it: they may belong to further department groups, and only the one set on them counts as theirs.
- Deleting a department, or turning it back into a plain group, leaves its people without a department. They stay in the workspace.

### Departments from the identity provider

Groups mirrored from the identity provider (see [Groups managed outside](user-groups.md#groups-managed-outside)) can be departments too, for example the groups made from the Entra _department_ attribute. A mirrored group does not become a department by itself: a workspace admin turns it into one (through the API, `PATCH .../user-groups/<id>/` with `{"kind": "department"}`; code and colour can then be set on the Departments page). After that:

- at each sign-in, a person the provider puts in that group and who has no department gets it as their department;
- a person who leaves the group at the provider loses the department;
- nobody can choose such a department by hand unless the provider already put them in it, because the provider decides who belongs to it;
- a department a person chose by hand is never replaced by the sign-in.

## API

- `GET /api/workspaces/<slug>/user-groups/?kind=department` lists the departments (in their order); `kind=group` lists the other groups. Create and change take `kind`, `code`, `color`, `sort_order` and `is_active` (workspace admins only).
- `GET /api/workspaces/<slug>/departments/` is the list for pickers: the departments that are switched on, open to every member of the workspace, guests included.
- `PATCH /api/workspaces/<slug>/members/<workspace member id>/department/` with `{"department": "<group id>"}` or `{"department": null}` sets a person's department: an admin anyone's, everybody else their own.
- The workspace members list and `workspace-members/me/` carry `department` (the id of the group).

## Not there yet

- The department is not asked for inside the onboarding steps or on the invitation page itself; the question comes when the person first opens the workspace, and it can be put off.
- RACI roles on work items, filters and notifications by department come with later changes.
