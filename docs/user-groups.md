# User groups

A workspace can organise its people into groups, for example by department or team, and assign work items to a whole group. Open **Settings → Groups** in the workspace.

## Groups and nesting

- A group has a name, a description and at most one parent group. Groups nest up to 10 levels deep, and a group cannot be moved under itself or one of its own subgroups.
- A name is unique among the groups with the same parent (upper and lower case do not matter).
- A person can belong to any number of groups, and only people who are active members of the workspace can join. Belonging to a group also means belonging to every group above it, so the members of a group are its own members plus those of all groups below it.
- Deleting a group needs its subgroups to be deleted or moved first. It removes the memberships and the work item assignments of the group.

## Who may change what

Everyone in the workspace except guests sees the groups. Changes are limited:

- **Workspace admins** manage every group and are the only ones who can create a top-level group.
- A **group admin** is a member with the role _Group admin_. They rule over their group and everything below it: they can change its members and their roles, and create, rename, move and delete subgroups. They cannot delete the group they administer, because that needs rule over its parent.
- Moving a group takes the same rights as deleting it where it is and creating it where it goes.

## Work items

A work item can be assigned to one or more groups, in the **Group assignees** row of the work item, next to the assignees. Belonging to such a group counts as being assigned to the work item for two project rules: a project's rule on who may change a work item (the assignee edit rule in the project settings), and who may log time on it.

## Groups managed outside

When people sign in with [single sign-on](sso.md#groups), their groups at the identity provider can be mirrored as groups. These groups are marked as managed outside:

- The provider is the only source. People are put in and taken out of them at each sign-in, and nobody can rename them, change their members or put a subgroup under them by hand. Group admins and workspace admins can still use them as work item assignees, and can place them under a group of their own (a local group as parent).
- The groups appear in every workspace the person belongs to, and a workspace they join later gets them at once, from what was read at the last sign-in.
- When a provider cannot be read at a sign-in, nothing changes. When it reports that the person is in no group, they are removed from the mirrored ones; memberships made by hand are never touched.
- A provider group whose name is already used by another top-level group is created as `Name (Entra)`, `Name (Google)` or `Name (SSO)`.

## API

The groups are served under `/api/workspaces/<slug>/user-groups/` (list and create), `.../user-groups/<id>/` (read, change, delete) and `.../user-groups/<id>/members/` with `.../members/<user id>/`. The members list takes `?nested=true` to include the groups below.
