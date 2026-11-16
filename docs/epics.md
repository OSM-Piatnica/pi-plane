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
