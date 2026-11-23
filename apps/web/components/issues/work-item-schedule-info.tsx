/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CalendarClock, Hourglass } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssue, TScheduleAnalysisItem } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// hooks
import { useFreshScheduleAnalysisItem } from "@/hooks/use-fresh-schedule-analysis-item";

type Props = {
  issue: TIssue;
  projectId: string;
};

const ScheduleInfoRows = observer(function ScheduleInfoRows({ item }: { item: TScheduleAnalysisItem }) {
  const { t } = useTranslation();
  const isCritical = item.is_critical;
  // dates are ISO "YYYY-MM-DD" strings, so they compare as text
  const isNeededByMissed = !!item.needed_by && item.earliest_finish > item.needed_by;

  return (
    <>
      <SidebarPropertyListItem icon={Hourglass} label={t("schedule_analysis.float")}>
        <span
          className={cn("px-2 text-body-xs-regular", isCritical ? "text-danger-primary" : "text-secondary")}
          title={t("schedule_analysis.float_help")}
          data-testid="work-item-float"
        >
          {isCritical
            ? t("schedule_analysis.float_critical")
            : t("schedule_analysis.float_days", { count: item.total_float })}
        </span>
      </SidebarPropertyListItem>
      {item.needed_by && (
        <SidebarPropertyListItem icon={CalendarClock} label={t("schedule_analysis.needed_by")}>
          <span
            className={cn("px-2 text-body-xs-regular", isNeededByMissed ? "text-danger-primary" : "text-secondary")}
            title={t("schedule_analysis.needed_by_help")}
            data-testid="work-item-needed-by"
          >
            {renderFormattedDate(item.needed_by)}
          </span>
        </SidebarPropertyListItem>
      )}
    </>
  );
});

/**
 * Float and "needed by" of a work item, read-only, from the critical path analysis of the timeline. Shown only while
 * the analysis is asked for (critical path on, or a Float column shown) and it covers this work item (a truncated one covers none); a completed
 * or cancelled work item has neither. "Needed by" is red when the earliest finish, not only the planned one, is late.
 */
export const WorkItemScheduleInfo = observer(function WorkItemScheduleInfo(props: Props) {
  const { issue, projectId } = props;
  const item = useFreshScheduleAnalysisItem(issue, { refreshProjectId: projectId });
  if (!item || item.is_fixed || item.total_float === null) return null;
  return <ScheduleInfoRows item={item} />;
});
