<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Critical path, float and "needed by"

Pi-Plane can tell which work items decide when a project ends. The analysis is the critical path method over the dated work items of a project and the dependencies between them. It runs on the server; the timeline only draws the result.

Based on the Gantt-RACI prototype by Paweł Niklewicz.

## Where it shows

- **Timeline, "Critical path" button** (next to "Roll up dates"), in a project, a module, a cycle and a project view. When it is on, the bars of critical work items get a red frame and the dependency lines between two critical work items are drawn red and heavier. The choice is remembered per browser. It is off by default, and nothing is computed while it is off.
- **Work item detail and peek view**, below "Duration", while the critical path is on:
  - **Float**: the working days the work item can slip without moving the end of the project, or "None (critical path)".
  - **Needed by**: shown when something that depends on the work item has a due date. In red when the work item is planned to finish after it.

In a module or a cycle the analysis covers only the work items of that module or cycle, so "the end" is the end of the module or cycle. A project view analyses the whole project, whatever the view filters. The timeline of epics has no critical path button.

The analysis is asked for again when a date, a state, a dependency or a lag of a work item on the timeline changes. A warning sign on the button says that the analysis is incomplete (see "Limits").

## The rules

Days are working days of the project, counted like everywhere else (see [working-days.md](working-days.md)): a start or finish on a weekend day counts as the nearest working day, and a lag counts working days.

| Question                                      | Rule                                                                                                                                                                                                                                                                                                                                                              |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What is analysed?                             | Work items with **both** a start and a finish date. Archived, deleted and draft work items take no part.                                                                                                                                                                                                                                                          |
| What about a work item with one date or none? | It is left out. If a dependency leads to it, the chain is cut there; the answer lists those work items (`undated_linked_ids`).                                                                                                                                                                                                                                    |
| Which dependencies count?                     | Blocked by / blocking (finish to start), starts before / after (start to start), finishes before / after (finish to finish) and starts before finish / finishes after start (start to finish), each with its lag. Other relations (relates to, duplicate, ...) have no dates and are ignored. So are dependencies on work items of another project.               |
| What is the earliest start?                   | Pi-Plane does not schedule by itself: people set the dates. The planned start is therefore the earliest start, unless a predecessor forces a later one. In a plan that keeps all its dependencies the earliest dates are simply the planned dates.                                                                                                                |
| When does the project end?                    | On the latest (earliest) finish among the analysed work items.                                                                                                                                                                                                                                                                                                    |
| What is the latest finish?                    | For a work item nothing depends on: the end of the project. Otherwise the latest day that still lets every work item depending on it start or finish by its own latest date.                                                                                                                                                                                      |
| What is float?                                | Working days between the earliest and the latest finish (total float).                                                                                                                                                                                                                                                                                            |
| What is critical?                             | A work item with no float. Any delay to it moves the end of the project.                                                                                                                                                                                                                                                                                          |
| Completed and cancelled work items            | Fixed points: their dates stay as they are and they have no float. They still hold back what depends on them (as the date rules do), but ask nothing of their predecessors: a late predecessor can no longer delay something that is done.                                                                                                                        |
| Due dates                                     | A due date never makes a work item critical: the critical path is about the end of the project only. Due dates give **needed by** instead: the latest finish of a work item that still lets every open work item downstream meet its due date. It is empty when nothing downstream has a due date. A work item's own due date is not part of its own "needed by". |
| Parents and sub-work items                    | The hierarchy is ignored. Every dated work item counts on its own; a parent is not a predecessor of its sub-work items and its dependencies do not pass down to them. A parent with dates of its own that span its sub-work items is analysed as one more work item.                                                                                              |
| Circles                                       | Work items that depend on each other in a circle are reported (`cycles`). The dependencies inside the circle are left out; those into and out of it still count.                                                                                                                                                                                                  |

A gap between two linked work items is float for the earlier one. Example: B is blocked by A, A finishes on Wednesday and B is planned for the following Monday. A can slip by two working days (Thursday and Friday) before B has to move, so A is not critical even when B is.

## Limits

- At most **2000** dated work items are analysed in one request: the first ones by start date. The answer then has `truncated: true` and the button shows a warning; the result only describes those work items.
- Nothing is cached. Every request computes the analysis from four queries. Cached results would have to be invalidated by every change of a date, a state, a relation, a lag, module or cycle membership, the project's weekend days, archiving and deletion, also from bulk operations and imports; computing takes a few milliseconds for a project of a few hundred work items.
- Holidays are not modelled, only the weekly pattern (as for durations).
- Float and "needed by" in the work item detail come from the analysis the timeline loaded. They do not appear when the critical path is off, or for a work item outside the analysed module or cycle.
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
  "cycles": [],
  "undated_count": 3,
  "undated_linked_ids": [],
  "weekend_days": [0, 6],
  "analysed_count": 10,
  "max_items": 2000,
  "truncated": false
}
```

`total_float` is `null` and `is_fixed` is `true` for completed and cancelled work items. `undated_count` counts the work items without both dates; `undated_linked_ids` lists those of them that a dependency links to an analysed work item.

The code is in `apps/api/plane/utils/schedule_analysis.py`; it reuses the dependency rules and working-day arithmetic of `issue_reschedule.py` and `work_item_duration.py`, so the analysis agrees with the date checks and with "move dependents".
