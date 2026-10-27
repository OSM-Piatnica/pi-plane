<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Weekend days and working days

Pi-Plane knows which days of the week are weekend days, and counts only working days for work item durations and relations.

## Where weekend days are set

- **Workspace:** the default for everyone. Saturday and Sunday unless changed.
- **Project:** copied from the workspace when the project is created, then its own. Changing it later recomputes the durations of the project's work items in the background.
- **Person:** optional. Left unset, a person follows the workspace; set, it overrides the workspace in views outside a project.

Inside a project the project's weekend days apply to everyone. Elsewhere (the workspace views, the profile) a person's own setting applies, otherwise the workspace's of the workspace they are in.

The first day of the week is set the same way, for workspaces and projects. New people take over the workspace's time zone.

## What counts working days

- **Duration** of a work item with a start and a due date counts the working days between them, at least 1. Calendars and the timeline shade the weekend days.
- **Relations** use the calendar of the dependent work item's project: the lag of a start-to-finish relation, "must start after" and the offer to move dependent work items all skip weekend days. Moving a work item keeps its length in working days.

## Upgrading

Migrations `0147` to `0149` add the settings and recompute the stored durations with Saturday and Sunday as weekend days for every existing project. Dates are not changed. If your team works on Saturdays, set the weekend days of the workspace before creating projects, or of each existing project afterwards.
