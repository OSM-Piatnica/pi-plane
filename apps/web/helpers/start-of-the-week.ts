/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EStartOfTheWeek } from "@plane/types";

type TStartOfTheWeekSources = {
  /** The person's own choice; null or undefined when they follow the project. */
  profile?: EStartOfTheWeek | null;
  project?: EStartOfTheWeek | null;
  workspace?: EStartOfTheWeek | null;
};

/** The first day of the week to show: the person's own choice, else the project's, else the workspace's, else Sunday. */
export const resolveStartOfTheWeek = ({ profile, project, workspace }: TStartOfTheWeekSources): EStartOfTheWeek =>
  profile ?? project ?? workspace ?? EStartOfTheWeek.SUNDAY;
