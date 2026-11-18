# Epics

An Epic is a work item that groups other work items. It is a work item type (a type marked as an Epic), so it has its own state, assignees and comments like any other work item. Epics are optional, per project.

## Turning Epics on

Open **Settings → Features** in the project. Work item types must be on first (the same page has that switch and the list of types the project can use). The **Epics** switch then links the workspace's Epic type to the project: the oldest active Epic type, created when the workspace has none. Other Epic types that admins made stay usable through the type list in workspace settings.

Turning Epics off keeps the Epics and their sub-work items as they are. It only stops new Epics and stops changing a type to Epic. Turning it on again restores everything. The Epic flag of a type cannot be changed while work items use the type.

## Rules

- An Epic has no parent. A work item cannot be its own parent, parent and child are in one project, and a change of parent cannot close a cycle. The server checks this for the app, the public API, the sub-work item endpoint and the work item import.
- Work items without a type count as "not an Epic".

## Epics and modules

Both answer "which bigger thing does this belong to", but they are different things. An **Epic** is a work item with children: one parent, its own state, assignee and comments. A **module** is a named group with its own dates, lead and status, and a work item can be in several. Modules and Epics do not depend on each other.

- Adding (or removing) a work item that has sub-work items to a module asks whether its sub-work items should follow. Yes copies the membership once, for all levels below. Nothing keeps them in step afterwards, because an Epic often spans modules.
- A new sub-work item starts in the modules of its parent. The form lets you change that.
- Epics are left out of the progress numbers of modules and cycles (totals, states, estimate points, assignee and label distributions, burndown), so an Epic is not counted next to its own children. They still show in the lists. Work items that have sub-work items but are not Epics count as before.

## Seeing the hierarchy

Useful in every project, with or without Epics:

- **Parent display property.** List and board rows show the parent of a work item as a chip with its identifier and name; clicking it opens the parent in the peek view. The spreadsheet has a display-only **Parent** column. It is a display property, so it can be turned off per view. Parents that are not part of the loaded page are fetched once per project, in batches, through the permission-scoped work item list, so a guest never receives a work item they cannot open (an unresolved parent shows a placeholder name).
- **Group by Parent.** Offered for the list and board layouts and as a board sub-group. One group per parent that the filtered work items reference, plus a "None" group for work items without a parent; a group's title is its parent's identifier and name. Sub-work items are always included under this grouping (the "Show sub-work items" option is not offered) and rows cannot be expanded, because children are already listed in their parent's group. Adding a work item in a parent group makes it a sub-work item of that parent. Dragging a work item to another parent group sets its parent (to none in the "None" group).
- **Group by Epic.** Offered for the list and board layouts and as a board sub-group, in projects that have an Epic type linked (and kept where a view already uses it). One group per Epic that the filtered work items sit under, and it holds the Epic and every work item below it, at any depth; "None" holds the work items that are under no Epic. It works with several Epic types. Like grouping by parent, it always includes sub-work items and rows do not expand. Adding a work item in an Epic group makes it a sub-work item of that Epic, and changing the parent of a work item reloads the groups, because only the server can tell which Epic is above it. The server finds the Epic with one bounded walk up the parent chain, only when this grouping (or the `epic` filter that loads more of a group) is asked for. Public boards do not offer it. Dragging a work item to another Epic group places it directly under that Epic (to no parent in "None"); a work item moves with its whole subtree. The server refuses a move that breaks the hierarchy rules (an Epic cannot get a parent, no cycle, a work item is not its own parent) and the toast says why.

## Work item type icon

List, board and spreadsheet rows show the icon of the type before the identifier, in projects that use work item types. The icon is the one an admin picked for the type in **Settings → Work item types** (an emoji or an icon); a type without one shows a built-in mark (a triangle for the Epic type, a general one for the rest). Hovering the mark shows the name of the type. It follows its own display property, **Work item Type**, which can be switched off per view. Only a short emoji or icon name with colours is accepted as a logo, nothing else (the API refuses any other shape).
