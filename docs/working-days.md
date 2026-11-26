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
- Clients of the API get a `400` with `error_code: relation_reschedule_available` and the list in `shifts`, and confirm by sending the same request again with `shift_dependents: true`. This holds for the app API, the public API (`/api/v1/`) and the timeline's bulk date update. For sub-work items, see "Parents and sub-work items" below.

### Due dates of moved work items

Moving a work item never changes its due date. When the new finish date of a work item that would be moved passes its due date, the list warns about it, for example "DEMO-41 will exceed its due date by 3 working days". The overrun counts the working days of that work item's project after the due date, up to the new finish date: a finish on the weekend right after a Friday due date is not late, and work that ends on Friday meets a due date on Saturday.

A work item that is late already is named only when the move makes it later still, with both figures: "DEMO-41 is already 1 working day past its due date and will exceed it by 4 working days". Work items without a due date or a finish date get no warning. The warning does not stop the move.

Each entry of `shifts`, `sub_items` and `shifts_with_sub_items` carries `target_date` (the due date), `deadline_overrun_days` (the working days past the due date after the move, or `null` when there is no warning) and `previous_deadline_overrun_days` (the overrun before the move, given only beside a warning for a work item that was late already).

### History

Each work item that was moved gets an activity entry per changed date that names and links the work item whose change caused it, for example "moved the start date to 15 Jan 2026 automatically after WDR-12 changed". Further down a chain the entry still names the work item the person changed, not the neighbour in between. The entry is recorded under the person who confirmed the move. The history endpoint returns the cause as `shift_cause` (`id`, `project_id`, `project_identifier`, `sequence_id`); it is empty once that work item is deleted. Shifts do not send notifications or emails and do not subscribe the person to the moved work items.

### Switching the offer off

Project settings, Workflows, Rules: **Offer to shift dependent work items** (on by default; also under the advanced options when creating a project; `is_reschedule_offer_enabled` in the API). With the setting off, a date change that breaks a dependency is refused with the dependency error (`relation_date_conflict`), as it was before the offer existed, and `shift_dependents` is ignored. Nothing else moves either: sub-work items are not offered and `move_sub_items` is ignored, so a moved parent is saved alone. The project of the work item being changed decides, also when its dependents are in other projects.

### Parents and sub-work items

A parent keeps its own start and finish dates; the timeline also draws the span of its sub-work items (the bracket, or the hatched bar of a parent without dates). Decision 15 of the roadmap (D8c) settled how the two meet:

| Situation                                       | What happens                                                                                                                                                                                                                                                       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A parent is moved, by hand or as a dependent    | Its sub-work items are listed in the same dialog, ticked by default. Ticked, each one moves by as many working days as the parent's start moved and keeps its own length; unticked, they stay. Nothing moves without the dialog.                                   |
| Only the parent's finish changes                | Its start did not move, so nothing is offered for the sub-work items.                                                                                                                                                                                              |
| A parent is moved earlier                       | Sub-work items follow it earlier too, except one that would then come too early for something it depends on: that one stays.                                                                                                                                       |
| Sub-work items that follow                      | Sub-work items at every level follow. Completed and cancelled ones, those you may not edit and those the change itself moves stay where they are. The ones that move take their own dependents along (listed in the dialog); the 100 work items limit counts them. |
| A sub-work item reaches past its parent's dates | For what depends on the parent, the parent counts with the wider span: a sub-work item that now ends after the parent's successor starts breaks that dependency. Pi-Plane offers to move the successor (or refuses the change when the offer is switched off).     |
| A parent without dates of its own               | It counts with the span of its sub-work items alone.                                                                                                                                                                                                               |
| An overrun that was already there               | Only a change that makes the parent's span later is checked against the parent's dependencies, so shortening a sub-work item that already overruns is allowed. A change to the successor itself is checked against the whole span.                                 |
| A parent that depends on something              | Sub-work items do not take over the predecessors of their parent: the parent's own dates are checked, its sub-work items may start earlier.                                                                                                                        |
| History                                         | A sub-work item that followed gets an activity entry per changed date naming the work item you changed, like any shifted dependent.                                                                                                                                |

The critical path and float (`docs/critical-path.md`) still take a parent with its own dates only.

For API clients: a request that changes dates may carry `offer_sub_items: true`; then a change that moves a parent with sub-work items is answered with a `400` offer even when it breaks no dependency (`original_error_code` is empty). The offer lists `shifts` (dependents that move when the sub-work items stay), `sub_items`, and `shifts_with_sub_items` (dependents that move when they follow). Confirm with `move_sub_items: true` or `false`, together with `shift_dependents: true` when the chosen list of dependents is not empty. A client that sends none of these flags sees no change: sub-work items never move, a change that breaks nothing is saved as it is, and `shift_dependents: true` alone moves only the dependents.

## Upgrading

- `0147` adds the first day of the week to workspaces and projects (Sunday), and sets every person whose personal setting was Sunday back to "follow the project"; other personal choices stay.
- `0148` adds the weekend days: Saturday and Sunday for every workspace and project, unset for people.
- `0149` recalculates the stored durations of work items that have both dates with Saturday and Sunday as weekend days. Dates are not changed.

If your team works on Saturdays, set the weekend days of the workspace before creating projects, and of each existing project afterwards.

## New people and time zones

Separately from all of the above: when someone finishes onboarding while their time zone is still the default (UTC), they take over the time zone of their last opened workspace (or the first one they joined), unless that is UTC too.
