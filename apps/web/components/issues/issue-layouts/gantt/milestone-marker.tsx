/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { getTimelineDatesText } from "@/components/gantt-chart/blocks/due-marker";
import type { TMilestoneDates } from "@/helpers/milestone";
import { isMilestoneLate } from "@/helpers/milestone";

type Props = {
  issueId: string;
  name: string | undefined;
  dates: TMilestoneDates;
  color: string | undefined;
  isMobile: boolean;
  onOpen: () => void;
};

/**
 * A milestone on the timeline: a diamond at its finish date (the end of its one-day block), red when the finish is
 * after its due date. The due date keeps its own marker.
 */
export function GanttMilestoneMarker(props: Props) {
  const { issueId, name, dates, color, isMobile, onOpen } = props;
  const { t } = useTranslation();
  const isLate = isMilestoneLate(dates.finish, dates.due);
  const label = [isLate ? t("work_item_types.milestone_after_due") : null, getTimelineDatesText(dates, t)]
    .filter(Boolean)
    .join(" · ");

  return (
    <Tooltip disabled={isMobile} layout="stacked" label={label}>
      <div
        id={`issue-${issueId}`}
        className="relative flex h-full w-full cursor-pointer items-center justify-end"
        // oxlint-disable-next-line prefer-tag-over-role -- the marker holds block content a <button> cannot contain
        role="button"
        tabIndex={0}
        onClick={onOpen}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onOpen();
        }}
      >
        <div
          data-testid="gantt-milestone-diamond"
          data-late={isLate}
          className={cn("mr-0.5 size-3.5 shrink-0 rotate-45 rounded-xs", isLate && "bg-danger-primary")}
          style={isLate ? undefined : { backgroundColor: color }}
        />
        <div className="absolute left-full flex max-w-[260px] items-center gap-1 truncate pl-2 text-13 whitespace-nowrap text-primary">
          <span className={cn("truncate", isLate && "text-danger-primary")}>{name}</span>
        </div>
      </div>
    </Tooltip>
  );
}
