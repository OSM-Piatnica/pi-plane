<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Critical path, float and "needed by"

Pi-Plane can tell which work items decide when a project ends. The analysis is the critical path method over the dated work items of a project and the dependencies between them. It runs on the server; the timeline only draws the result.

Based on the Gantt-RACI prototype by Paweł Niklewicz.

## Where it shows

- **Timeline, "Critical path" button** (next to "Roll up dates"), in a project, a module, a cycle and a project view. When it is on, the bars of critical work items get a red frame and the critical dependencies (see "Critical dependencies" below) are drawn red and heavier. The choice is remembered per browser. It is off by default, and nothing is computed while it is off.
- **Work item detail and peek view**, below "Duration", while the critical path is on:
  - **Float**: the working days the work item can slip without moving the end of the project, or "None (critical path)".
  - **Needed by**: shown when something that depends on the work item has a due date. In red when the work item's earliest finish is after it (its planned finish, or later where a dependency pushes it).

In a module or a cycle the analysis covers only the work items of that module or cycle, so "the end" is the end of the module or cycle. A project view analyses the whole project, whatever the view filters. The timeline of epics has no critical path button.

The analysis is asked for again when a date, a state, a dependency or a lag of a work item on the timeline changes. While a new answer is on its way the previous one stays on screen, except in the work item detail for a work item that was just changed there: its Float and Needed by are hidden until an answer that reflects the change arrives. A warning sign on the button says that the analysis is incomplete (see "Limits").

## The rules

Days are working days of the project, counted like everywhere else (see [working-days.md](working-days.md)): a start or finish on a weekend day counts as the nearest working day, and a lag counts working days.

| Question                                      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What is analysed?                             | Work items with **both** a start and a finish date. Archived, deleted and draft work items take no part.                                                                                                                                                                                                                                                                                                                                                                           |
| What about a work item with one date or none? | It is left out. If a dependency leads to it, the chain is cut there; the answer lists those work items (`undated_linked_ids`). A work item whose finish is before its start is left out the same way and counted on its own (`inverted_count`); the button warns about it.                                                                                                                                                                                                         |
| Which dependencies count?                     | Blocked by / blocking (finish to start), starts before / after (start to start), finishes before / after (finish to finish) and starts before finish / finishes after start (start to finish), each with its lag. Other relations (relates to, duplicate, ...) have no dates and are ignored. So are dependencies on work items of another project.                                                                                                                                |
| What is the earliest start?                   | Pi-Plane does not schedule by itself: people set the dates. The planned start is therefore the earliest start, unless a predecessor forces a later one. In a plan that keeps all its dependencies the earliest dates are simply the planned dates.                                                                                                                                                                                                                                 |
| When does the project end?                    | On the latest (earliest) finish among the analysed work items.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| What is the latest finish?                    | For a work item nothing depends on: the end of the project. Otherwise the latest day that still lets every work item depending on it start or finish by its own latest date.                                                                                                                                                                                                                                                                                                       |
| What is float?                                | Working days between the earliest and the latest finish (total float).                                                                                                                                                                                                                                                                                                                                                                                                             |
| What is critical?                             | A work item with no float. Any delay to it moves the end of the project.                                                                                                                                                                                                                                                                                                                                                                                                           |
| Critical dependencies                         | A dependency is critical when both its work items are critical **and** it drives the later one: the date it asks for is the later work item's earliest date. A dependency between two critical work items that leaves the later one room is not critical (`critical_links` lists the critical ones).                                                                                                                                                                               |
| Completed and cancelled work items            | Fixed points: their dates stay as they are and they have no float. They still hold back what depends on them (as the date rules do), but ask nothing of their predecessors: a late predecessor can no longer delay something that is done.                                                                                                                                                                                                                                         |
| Due dates                                     | A due date never makes a work item critical: the critical path is about the end of the project only. Due dates give **needed by** instead: the latest finish of a work item that still lets every open work item downstream meet its due date. Completed and cancelled work items stop the chain: their due dates, and those beyond them, do not count. It is empty when nothing counted downstream has a due date. A work item's own due date is not part of its own "needed by". |
| Parents and sub-work items                    | The hierarchy is ignored. Every dated work item counts on its own; a parent is not a predecessor of its sub-work items and its dependencies do not pass down to them. A parent with dates of its own that span its sub-work items is analysed as one more work item.                                                                                                                                                                                                               |
| Circles                                       | Work items that depend on each other in a circle are reported (`cycles`). The dependencies inside the circle are left out; those into and out of it still count.                                                                                                                                                                                                                                                                                                                   |

A gap between two linked work items is float for the earlier one. Example: B is blocked by A, A finishes on Wednesday and B is planned for the following Monday. A can slip by two working days (Thursday and Friday) before B has to move, so A is not critical even when B is.

## Limits

- At most **2000** dated work items are analysed in one request: the first ones by start date (work items whose finish is before their start do not count). The answer then has `truncated: true` and only describes a cut-off part of the plan, so the timeline highlights nothing and the work item detail shows no Float or Needed by; the button shows a warning.
- Nothing is cached. Every request computes the analysis from five queries. Cached results would have to be invalidated by every change of a date, a state, a relation, a lag, module or cycle membership, the project's weekend days, archiving and deletion, also from bulk operations and imports; computing takes a few milliseconds for a project of a few hundred work items.
- Holidays are not modelled, only the weekly pattern (as for durations).
- Float and "needed by" in the work item detail come from the analysis the timeline loaded. They do not appear when the critical path is off, when the analysis is truncated, or for a work item outside the analysed module or cycle.
- There is no "Float" column in the list and spreadsheet layouts yet.

## API

`GET /api/workspaces/<slug>/projects/<project_id>/schedule-analysis/`

Optional query parameters: `module=<id>` or `cycle=<id>`.

Any project member may call it. A guest of a project that does not let guests see all work items gets the analysis of their own work items only, as in work item lists.

```json
{
  "project_start": "2027-06-07",
  "project_end": "2027-07-09",
  "items": {
    "<work item id>": {
      "earliest_start": "2027-06-15",
      "earliest_finish": "2027-06-28",
      "latest_start": "2027-06-21",
      "latest_finish": "2027-07-02",
      "total_float": 4,
      "is_critical": false,
      "is_fixed": false,
      "needed_by": "2027-06-29"
    }
  },
  "critical_ids": ["<work item id>"],
  "critical_links": [{ "source": "<work item id>", "target": "<work item id>", "relation_type": "blocking" }],
  "cycles": [],
  "undated_count": 3,
  "inverted_count": 0,
  "undated_linked_ids": [],
  "weekend_days": [0, 6],
  "analysed_count": 10,
  "max_items": 2000,
  "truncated": false
}
```

`total_float` is `null` and `is_fixed` is `true` for completed and cancelled work items. `undated_count` counts the work items without both dates; `inverted_count` counts those whose finish is before their start; `undated_linked_ids` lists the left-out work items of both kinds that a dependency links to an analysed work item. In `critical_links`, `source` is the work item that comes first and `relation_type` is the dependency seen from it (`blocking`, `start_before`, `finish_before` or `start_before_finish`).

The code is in `apps/api/plane/utils/schedule_analysis.py`; it reuses the dependency rules and working-day arithmetic of `issue_reschedule.py` and `work_item_duration.py`, so the analysis agrees with the date checks and with "move dependents".

## Filtering by the critical path

The work item filters of a project, module, cycle and project view have a **Critical path** filter (Yes or No). **Yes** lists the critical work items (float 0), **No** every other work item, including undated, completed and cancelled ones, which the analysis does not rate. It combines with the other filters and can be saved in a view.

It is judged by the same analysis as the timeline, always of the whole project, module or cycle the list belongs to, not of what the other filters leave: a work item is critical or not before any other filter is applied. The filter is not offered in workspace views, on the profile pages and in the archive, because their lists are not of one project.

Rules and limits:

- Where the analysis is truncated (more than 2000 dated work items, see "Limits"), the list answers with an error (`critical_filter_truncated`) instead of leaving out work items without telling. A saved view with this filter in such a project therefore shows an error until the filter is removed.
- Each list request that uses the filter runs the analysis once (not once per condition), so such a request costs about as much as one request of the endpoint above.
- A guest who only sees their own work items gets the critical path of those alone, as in the analysis.

API: `is_critical` (or `is_critical__exact`) with `true` or `false` in the `filters` parameter of the work item list endpoints of a project, a module and a cycle, for example `filters={"is_critical": true}`. On an endpoint that is not of one project it answers `critical_filter_needs_project`.
