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

The order differs from weekend days: **the person's own choice wins everywhere**, including inside a project; otherwise the project's, then the workspace's, then Monday. New workspaces and projects start their week on Monday (`0155`; existing ones keep their day). The time buckets of the "group by due / finish / start date" views are different: they use the project's first day of the week (else the workspace's) and ignore the personal choice, so everyone looking at a project sees the same groups.

## What counts working days

- **Duration** of a work item with a start and a finish date counts the working days between them, at least 1. The due date is a deadline and plays no part in it.
- **Calendars and the timeline:** weekend days are shaded. The calendar hides weekend columns by default (the "Show weekends" option shows them); the timeline shades them in its week and month views.
- **Relations** use the calendar of the dependent work item's project. The **lag** of a relation (the "Lag (days)" field, ±3650 days, available on every timeline relation type, not only start-to-finish) counts working days; a start or finish on a weekend day counts as the nearest working day. With a lag of zero a work item that must start after another finishes starts on the next working day.
- **Moving dependents:** when a work item's dates change and others depend on it, Pi-Plane offers to move them, keeping each one's length in working days. See the next section.

## Moving dependent work items

A date change that would make a dependent work item start or finish too early is not saved straight away. Pi-Plane lists the dependent work items with their new dates and asks whether to move them; on "Move them" the change and the shifts are saved together. The shift follows the chain: a work item that moves takes its own dependents along.

- Work items only move later, never earlier. Each keeps its length in working days of its own project.
- Nothing is offered, and the change stays refused, when a dependent is in a completed or cancelled state, when you may not edit one of them, when more than 100 work items would move, or when the changed work item itself would come too early for something it depends on.
- Clients of the API get a `400` with `error_code: relation_reschedule_available` and the list in `shifts`, and confirm by sending the same request again with `shift_dependents: true`. This holds for the app API, the public API (`/api/v1/`) and the timeline's bulk date update.

### History

Each work item that was moved gets an activity entry per changed date that names and links the work item whose change caused it, for example "moved the start date to 15 Jan 2026 automatically after WDR-12 changed". Further down a chain the entry still names the work item the person changed, not the neighbour in between. The entry is recorded under the person who confirmed the move. The history endpoint returns the cause as `shift_cause` (`id`, `project_id`, `project_identifier`, `sequence_id`); it is empty once that work item is deleted. Shifts do not send notifications or emails and do not subscribe the person to the moved work items.

### Switching the offer off

Project settings, Workflows, Rules: **Offer to shift dependent work items** (on by default; also under the advanced options when creating a project; `is_reschedule_offer_enabled` in the API). With the setting off, a date change that breaks a dependency is refused with the dependency error (`relation_date_conflict`), as it was before the offer existed, and `shift_dependents` is ignored. The project of the work item being changed decides, also when its dependents are in other projects.

### Parents and sub-work items

The dates a parent shows on the timeline from its sub-work items (the bracket, or the hatched bar of a parent without dates) are only drawn there. A parent keeps its own start and finish dates, and dependencies are checked against those. Sub-work items do not take over the dependencies of their parent. So:

- Moving a parent moves the work items that depend on the parent. Its sub-work items stay where they are.
- A parent that is moved as a dependent takes its own dependents along, again without its sub-work items.
- A sub-work item that is moved, by hand or as a dependent, does not change its parent's dates, and nothing that depends on the parent moves, even when the sub-work item now ends after the parent.
- A parent without dates of its own holds nothing back: a dependency on it has no date to check.

## Upgrading

- `0147` adds the first day of the week to workspaces and projects (Sunday), and sets every person whose personal setting was Sunday back to "follow the project"; other personal choices stay.
- `0148` adds the weekend days: Saturday and Sunday for every workspace and project, unset for people.
- `0149` recalculates the stored durations of work items that have both dates with Saturday and Sunday as weekend days. Dates are not changed.

If your team works on Saturdays, set the weekend days of the workspace before creating projects, and of each existing project afterwards.

## New people and time zones

Separately from all of the above: when someone finishes onboarding while their time zone is still the default (UTC), they take over the time zone of their last opened workspace (or the first one they joined), unless that is UTC too.
