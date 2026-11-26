<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Baselines

A baseline is a saved plan of a project: the dates its work items had at the moment somebody saved it. The timeline can then show where each work item was planned, next to where it is now, and how many working days it moved.

Based on the Gantt-RACI prototype by Paweł Niklewicz.

## Where it shows

- **Timeline, "Baseline" button** (next to "Roll up dates" and "Critical path"), in a project, a module, a cycle and a project view. Also on the timeline of epics. The menu has:
  - **Show baseline**: on or off. Off by default; the choice is remembered per browser. Nothing is fetched while it is off.
  - **Save baseline** (project admins and members): asks for a name, with "Baseline" and today's date as the default. The new baseline becomes the active one, and the timeline starts showing it.
  - **Saved baselines**, newest first, the active one marked. Picking one compares the timeline with it, for this visit only. Admins and members can also make one the active baseline, rename it or delete it.
- **When shown**, for each work item whose start or finish moved since the baseline:
  - a thin grey bar under the work item's bar, from the saved start to the saved finish (above the bar for a parent with a roll-up bracket, which sits below it);
  - the difference of the finish in working days next to the bar, "+3 d" in red when later, "−2 d" in green when earlier (of the start when the work item has no finish);
  - the tooltip of the grey bar has the saved dates and the difference of the start and the finish;
  - a hollow grey diamond where the saved due date was, when the due date moved since. The due date is a deadline, not part of the schedule, so it has no number of days.
- The button itself shows how far the end of the plan moved (the latest finish then and now), and says it in its tooltip.

The comparison is asked for again when a date of a work item on the timeline changes, and when another baseline is picked, saved, made active or deleted. It works together with the critical path, the roll-up brackets and the shading of weekend days.

## The rules

| Question                              | Rule                                                                                                                                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What is saved?                        | Every work item of the project that is not deleted, archived, a draft or in triage and has a start, a finish or a due date: its `start_date`, `finish_date`, `target_date`, the group of its state and `completed_at`.                      |
| And work items without any date?      | Not saved: there is nothing to compare later. If one gets dates afterwards, it shows as not in the baseline.                                                                                                                                |
| What is compared?                     | The schedule: the start and the finish, like the timeline bar. The due date is answered (saved and current) but never counts as variance.                                                                                                   |
| In what unit?                         | Working days of the project (see [working-days.md](working-days.md)), positive when the date is later than planned. A start on a weekend day counts as the next working day, a finish as the previous one: Friday to Saturday is no change. |
| A work item created after the save?   | It has no baseline dates and no variance, and no grey bar.                                                                                                                                                                                  |
| A work item deleted or archived since | Left out of the comparison and of the baseline's list of items.                                                                                                                                                                             |
| A date cleared since                  | The saved date is still answered; the difference is empty.                                                                                                                                                                                  |
| Active baseline                       | At most one per project, enforced by the database. Saving a new baseline makes it active; any other can be made active; deleting the active one leaves the project without one. Older baselines are kept.                                   |
| How many?                             | At most **20** baselines per project. Saving one more is refused; delete one first.                                                                                                                                                         |
| Module, cycle, project view           | A module or a cycle timeline compares the work items of that module or cycle. A project view compares the whole project, whatever the view filters.                                                                                         |

## Who may do what

| Role                                               | Read and show | Save, rename, make active, delete |
| -------------------------------------------------- | ------------- | --------------------------------- |
| Project admin, member (and workspace admins in it) | yes           | yes                               |
| Guest                                              | yes           | no                                |
| Not a member of the project                        | no            | no                                |

Members may manage baselines because they plan the work; a baseline changes no work item. A guest of a project that does not let guests see all work items sees only the work items they created, in the comparison and in a baseline's items, and not the number of work items a baseline holds.

## Limits

- Holidays are not modelled, only the weekly pattern (as for durations).
- No "Variance" column in the list and spreadsheet layouts yet: it needs the comparison loaded outside the timeline, as the Float column does for the critical path.
- No "what if": shifts that are not saved cannot be compared with the baseline.
- Saving reads the work items in one query and writes the rows in bulk, in one transaction; nothing is computed until the comparison is asked for.

## API

All under `/api/workspaces/<slug>/projects/<project_id>/`.

| Method and path           | What                                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------------------------- |
| `GET baselines/`          | `{"baselines": [...], "max_baselines": 20}`, newest first                                                 |
| `POST baselines/`         | `{"name": "...", "description": "..."}` saves the current plan; `400` with `code: baseline_limit_reached` |
| `GET baselines/<id>/`     | the baseline with its `items` (work item, start, finish, due date, state group, completed at)             |
| `PATCH baselines/<id>/`   | `name`, `description`, `is_active`                                                                        |
| `DELETE baselines/<id>/`  | removes it                                                                                                |
| `GET baselines/variance/` | the comparison with the active baseline; `?baseline=<id>`, `?module=<id>`, `?cycle=<id>`                  |

```json
{
  "baseline": { "id": "...", "name": "Plan 2027-06-01", "is_active": true, "item_count": 42, "...": "..." },
  "items": {
    "<work item id>": {
      "in_baseline": true,
      "baseline_start_date": "2027-06-01",
      "start_date": "2027-06-03",
      "start_date_variance": 2,
      "baseline_finish_date": "2027-06-04",
      "finish_date": "2027-06-09",
      "finish_date_variance": 3,
      "baseline_target_date": "2027-06-11",
      "target_date": "2027-06-18"
    }
  },
  "summary": { "baseline_end": "2027-06-30", "current_end": "2027-07-02", "end_variance": 2 },
  "weekend_days": [0, 6]
}
```

Without an active baseline (and none asked for), `baseline` is `null` and `items` is empty. The tables are `project_baselines` and `project_baseline_items` (migration `0162_project_baselines`); the code is in `apps/api/plane/utils/baselines.py` and `apps/api/plane/app/views/project/baseline.py`.
