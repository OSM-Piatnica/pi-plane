<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Weekend days and working days

Pi-Plane knows which days of the week are weekend days, and counts only working days for work item durations and relations.

## Where weekend days are set

| Level     | Who sets it                         | Where                                                            | Default                               |
| --------- | ----------------------------------- | ---------------------------------------------------------------- | ------------------------------------- |
| Workspace | Workspace admins                    | Workspace settings                                               | Saturday and Sunday                   |
| Project   | Project admins and workspace admins | The project's settings form                                      | Copied from the workspace on creation |
| Person    | The person                          | Profile, Preferences (with "Use the workspace default" to reset) | Unset: follows the workspace          |

Any number of days from none to six can be weekend days; marking all seven is refused.

Inside a project the project's weekend days apply to everyone. Elsewhere (the workspace views, the profile) a person's own setting applies if there is one, otherwise the workspace's of the workspace they are in. Changing the workspace's weekend days affects only projects created afterwards.

Changing a project's weekend days recalculates the **duration** of its work items that have both dates, in the background. The dates are not changed. Archived work items are included.

## First day of the week

Workspaces and projects have a first day of the week, a project copies the workspace's when it is created, and people can choose their own (Profile, Preferences, with a "Project default" option). It affects calendars, the timeline and date pickers.

The order differs from weekend days: **the person's own choice wins everywhere**, including inside a project; otherwise the project's, then the workspace's, then Sunday.

## What counts working days

- **Duration** of a work item with a start and a due date counts the working days between them, at least 1.
- **Calendars and the timeline:** weekend days are shaded. The calendar hides weekend columns by default (the "Show weekends" option shows them); the timeline shades them in its week and month views.
- **Relations** use the calendar of the dependent work item's project. The **lag** of a relation (the "Lag (days)" field, ±3650 days, available on every timeline relation type, not only start-to-finish) counts working days; a start or finish on a weekend day counts as the nearest working day. With a lag of zero a work item that must start after another finishes starts on the next working day.
- **Moving dependents:** when a work item's dates change and others depend on it, Pi-Plane offers to move them, keeping each one's length in working days. It never moves work items in a completed or cancelled state, ones you may not edit, or more than 100 items; if any of these applies no move is offered and the change stays refused.

## Upgrading

- `0147` adds the first day of the week to workspaces and projects (Sunday), and sets every person whose personal setting was Sunday back to "follow the project"; other personal choices stay.
- `0148` adds the weekend days: Saturday and Sunday for every workspace and project, unset for people.
- `0149` recalculates the stored durations of work items that have both dates with Saturday and Sunday as weekend days. Dates are not changed.

If your team works on Saturdays, set the weekend days of the workspace before creating projects, and of each existing project afterwards.

## New people and time zones

Separately from all of the above: when someone finishes onboarding while their time zone is still the default (UTC), they take over the time zone of their last opened workspace (or the first one they joined), unless that is UTC too.
