/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { ChevronDownOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { IGanttBlock } from "@plane/types";
import { Row } from "@plane/blocks/layout";
import { cn } from "@plane/utils";
// components
import { useGanttSubWorkItems } from "@/components/gantt-chart/contexts";
import { MultipleSelectEntityAction } from "@/components/core/multiple-select";
import { IssueGanttSidebarBlock } from "@/components/issues/issue-layouts/gantt/blocks";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import type { TSelectionHelper } from "@/hooks/use-multiple-select";
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
// local imports
import { BLOCK_HEIGHT, GANTT_SELECT_GROUP } from "../../constants";

type Props = {
  block: IGanttBlock;
  enableSelection: boolean;
  isDragging: boolean;
  selectionHelpers?: TSelectionHelper;
  isEpic?: boolean;
};

export const IssuesSidebarBlock = observer(function IssuesSidebarBlock(props: Props) {
  const { block, enableSelection, isDragging, selectionHelpers, isEpic = false } = props;
  // store hooks
  const { updateActiveBlockId, isBlockActive, getNumberOfDaysFromPosition } = useTimeLineChartStore();
  const { getIsIssuePeeked } = useIssueDetail();
  const { t } = useTranslation();
  const subWorkItems = useGanttSubWorkItems();

  const isBlockComplete = !!block?.start_date && !!block?.target_date;
  const duration = isBlockComplete ? getNumberOfDaysFromPosition(block?.position?.width) : undefined;

  if (!block?.data) return null;

  const isIssueSelected = selectionHelpers?.getIsEntitySelected(block.id);
  const isIssueFocused = selectionHelpers?.getIsEntityActive(block.id);
  const isBlockHoveredOn = isBlockActive(block.id);
  // sub-work items: indentation for the nested rows and a chevron for the work items that have some
  const level = subWorkItems?.levelById[block.id] ?? 0;
  const hasSubWorkItems = (block.data.sub_issues_count ?? 0) > 0;
  const isExpanded = !!subWorkItems?.expandedIds.has(block.id);
  const isLoadingSubWorkItems = !!subWorkItems?.loadingIds.has(block.id);

  return (
    <div
      className={cn("group/list-block", {
        "rounded-sm bg-layer-1": isDragging,
        "rounded-l-sm border border-r-0 border-accent-strong": getIsIssuePeeked(block.data.id),
        "border border-r-0 border-strong-1": isIssueFocused,
      })}
      onMouseEnter={() => updateActiveBlockId(block.id)}
      onMouseLeave={() => updateActiveBlockId(null)}
    >
      <Row
        className={cn(
          "group flex w-full items-center gap-2 bg-layer-transparent pr-4 hover:bg-layer-transparent-hover",
          {
            "bg-layer-transparent-hover": isBlockHoveredOn,
            "bg-accent-primary/5 hover:bg-accent-primary/10": isIssueSelected,
            "bg-accent-primary/10": isIssueSelected && isBlockHoveredOn,
          }
        )}
        style={{
          height: `${BLOCK_HEIGHT}px`,
        }}
      >
        {enableSelection && selectionHelpers && (
          <div className="absolute left-1 flex items-center gap-2">
            <MultipleSelectEntityAction
              className={cn(
                "pointer-events-none opacity-0 transition-opacity group-hover/list-block:pointer-events-auto group-hover/list-block:opacity-100",
                {
                  "pointer-events-auto opacity-100": isIssueSelected,
                }
              )}
              groupId={GANTT_SELECT_GROUP}
              id={block.id}
              selectionHelpers={selectionHelpers}
            />
          </div>
        )}
        {subWorkItems && (
          <div className="flex h-full shrink-0 items-center" style={{ paddingLeft: `${level * 16}px` }}>
            {hasSubWorkItems ? (
              <button
                type="button"
                className="flex size-5 items-center justify-center rounded-sm text-tertiary hover:bg-layer-1 hover:text-primary"
                aria-expanded={isExpanded}
                aria-label={isExpanded ? t("sub_work_item.collapse") : t("sub_work_item.expand")}
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  subWorkItems.toggle(block.id);
                }}
              >
                <ChevronDownOutline
                  className={cn("size-3.5 transition-transform", {
                    "-rotate-90": !isExpanded,
                    "animate-pulse": isLoadingSubWorkItems,
                  })}
                />
              </button>
            ) : (
              <span className="size-5" aria-hidden />
            )}
          </div>
        )}
        <div className="flex h-full flex-grow items-center justify-between gap-2 truncate">
          <div className="flex-grow truncate">
            <IssueGanttSidebarBlock issueId={block.data.id} isEpic={isEpic} />
          </div>
          {duration && (
            <div className="flex-shrink-0 text-13 text-secondary">
              <span>
                {duration} day{duration > 1 ? "s" : ""}
              </span>
            </div>
          )}
        </div>
      </Row>
    </div>
  );
});
