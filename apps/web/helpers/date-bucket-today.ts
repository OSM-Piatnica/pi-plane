/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EStartOfTheWeek } from "@plane/types";
import type { TBucketToday } from "@plane/utils";
import { getTodayInTimeZone } from "@plane/utils";
import { resolveStartOfTheWeek } from "@/helpers/start-of-the-week";

/**
 * The day the time buckets of a date are counted from: today in the person's profile time zone, which is what the
 * API uses to bucket (the browser's own zone only when no zone is known).
 */
export const getBucketToday = (timeZone?: string | null): TBucketToday =>
  timeZone ? getTodayInTimeZone(timeZone) : new Date();

/** What the buckets need from the root store: the person, the project being viewed and the workspace. */
type TBucketStore = {
  user: { data?: { user_timezone?: string | null } | null };
  router: { projectId?: string | null };
  projectRoot: {
    project: { getProjectById: (projectId: string) => { start_of_the_week?: EStartOfTheWeek } | undefined };
  };
  workspaceRoot: { currentWorkspace: { start_of_the_week?: EStartOfTheWeek } | null };
};

/**
 * Today and the first day of the week the buckets of the list being viewed are counted by. Like the API, a list
 * inside a project uses that project's start of the week and any other list (the profile page, which mixes
 * projects) the workspace's, so the whole list shares one definition of "this week". The person's own
 * start-of-the-week setting is not used: two people looking at the same project must see the same groups.
 */
export const getBucketContext = (store: TBucketStore): { today: TBucketToday; weekStart: number } => {
  const projectId = store.router.projectId;
  return {
    today: getBucketToday(store.user.data?.user_timezone),
    weekStart: resolveStartOfTheWeek({
      project: projectId ? store.projectRoot.project.getProjectById(projectId)?.start_of_the_week : undefined,
      workspace: store.workspaceRoot.currentWorkspace?.start_of_the_week,
    }),
  };
};
