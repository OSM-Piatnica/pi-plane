<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Focus: next work items and blockers

The focus endpoint answers, for the person who asks, what to do next, what holds their work up, whose work waits
for theirs, what their department has to approve and what is late. It is the data source of the "My tasks" app
(Lite, workstream E of the roadmap) and of a "My view" panel in the project; neither is built yet.

## The lists

| List            | What is in it                                                                                                   | Order                                                      |
| --------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `next`          | my open work items; `startable` says whether a predecessor still holds up the start                             | startable first, then start date, then planned finish date |
| `blocked`       | my open work items that a predecessor holds up, with the predecessors (`blocked_by`) and their assignees        | start date, then planned finish date                       |
| `waiting_on_us` | open work items of other people that one of my open work items holds up, with mine that do it (`waiting_on`)    | start date, then planned finish date                       |
| `to_approve`    | open work items on which one of my departments is the approver ([RACI](raci.md)), with those departments        | due date, then planned finish date                         |
| `overdue`       | my open work items whose due date (`target_date`) or planned finish (`finish_date`) is before today (`overdue`) | due date, then planned finish date                         |

- **My work items** are those assigned to me, directly or through a group I belong to (a group assignment counts
  for the members of the groups below it too).
- **My departments** are all the active departments I belong to directly. One department per person is the rule
  today ([#508](https://github.com/OSM-Piatnica/pi-plane/issues/508)); the lists take every one there is, so they
  keep working if that rule changes.
- **Open** means a state outside the completed and cancelled groups. Archived, draft and triage work items, and
  those of archived projects, never take part.
- **Today** is the date in the person's time zone (their profile setting).
- Each list is `{"count": <all that match>, "items": [<the first ones>]}`; 50 items per list by default.

## What holds a work item up

Only the relations with dates hold work up, each until its predecessor has got far enough:

| Relation, seen from the work item | The predecessor has to be | Until then the work item cannot |
| --------------------------------- | ------------------------- | ------------------------------- |
| Blocked by                        | completed or cancelled    | start                           |
| Starts after                      | started (or further)      | start                           |
| Finishes after                    | completed or cancelled    | finish                          |
| Finishes after start              | started (or further)      | finish                          |

The lag of a relation is not checked: the lists say what has to happen before, not when. A work item held up only
in its finish is still startable, and is listed under `blocked` with `holds: "finish"`. "Relates to", "duplicate"
and the other relations without dates hold nothing up. A predecessor may be in another project; it is shown if the
person may see it.

## Who sees what

The lists hold only work items the person may see, by the same rules as the work item lists: those of the
projects they are an active member of; in a project where guests do not see everything, a guest sees only the work
items they created. A predecessor the person may not see is counted (`hidden_blocked_by_count`), not shown. A
person who is not a member of the workspace gets `403`.

## API

- `GET /api/workspaces/<slug>/focus/` across the person's projects, and
  `GET /api/workspaces/<slug>/projects/<project_id>/focus/` for one project (the predecessors may still be
  elsewhere).
- `?limit=` sets the number of items per list, from 1 to 200 (50 by default); `count` is always the full number.
- Every work item carries `id`, `name`, `sequence_id`, `project_id`, `project_identifier`, `state_id`,
  `state_group`, `priority`, `start_date`, `finish_date`, `target_date`, `assignee_ids` and `group_assignee_ids`.
- A predecessor entry is `{"relation_type": "blocked_by" | "start_after" | "finish_after" | "finish_after_start",
"holds": "start" | "finish", "issue": {...}}`.
- The answer also has `today`, `department_ids` (mine) and `raci_enabled` (whether the workspace has RACI on;
  `to_approve` is empty while it is off, and only counts projects that have RACI on).

The number of database queries is the same however many work items there are (about twenty per request); nothing
is cached.

## Not there yet

- Approval steps of acceptances (step C1 of the roadmap) join `to_approve` when they exist; today it holds only
  the RACI approver.
- The web parts: "Blocked by" and "Blocking" summaries with owner and date in work item detail, a "Next" hint when
  a work item is completed and the "My view" panel in the project; then the Lite home (E1).
