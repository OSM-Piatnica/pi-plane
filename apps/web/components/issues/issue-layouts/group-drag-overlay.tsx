/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { WarningCircleOutline } from "@makeplane/propel/icons";
// plane imports
import { ISSUE_ORDER_BY_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TIssueOrderByOptions } from "@plane/types";
// helpers
import { cn, getIssueOrderByField } from "@plane/utils";
import { WorkFlowDisabledOverlay } from "@/components/workflow";
import {
  COMPLETED_CYCLE_DROP_ERROR,
  DATE_BUCKET_DROP_ERROR,
  DATE_BUCKET_NO_DAY_LEFT_ERROR,
} from "@/helpers/group-column";

type Props = {
  dragColumnOrientation: "justify-start" | "justify-center" | "justify-end";
  workflowDisabledSource?: string;
  canOverlayBeVisible: boolean;
  isDropDisabled: boolean;
  dropErrorMessage?: string;
  orderBy: TIssueOrderByOptions | undefined;
  isDraggingOverColumn: boolean;
  isEpic?: boolean;
};

export function GroupDragOverlay(props: Props) {
  const {
    dragColumnOrientation,
    canOverlayBeVisible,
    workflowDisabledSource,
    isDropDisabled,
    dropErrorMessage,
    orderBy,
    isDraggingOverColumn,
    isEpic = false,
  } = props;
  // hooks
  const { t } = useTranslation();
  // refs
  const messageContainerRef = useRef<HTMLDivElement>(null);

  const shouldOverlayBeVisible = isDraggingOverColumn && canOverlayBeVisible;
  const readableOrderBy = t(
    ISSUE_ORDER_BY_OPTIONS.find((orderByObj) => orderBy && orderByObj.key === getIssueOrderByField(orderBy))
      ?.titleTranslationKey || ""
  );

  return (
    <div
      ref={messageContainerRef}
      className={cn(
        `absolute top-0 left-0 h-full w-full items-center rounded-sm bg-layer-1/85 text-13 font-medium text-tertiary ${dragColumnOrientation}`,
        {
          "z-2 flex flex-col border-[1px] border-strong": shouldOverlayBeVisible,
          "bg-danger-subtle": workflowDisabledSource && isDropDisabled,
        },
        { hidden: !shouldOverlayBeVisible }
      )}
    >
      {workflowDisabledSource ? (
        <WorkFlowDisabledOverlay
          messageContainerRef={messageContainerRef}
          workflowDisabledSource={workflowDisabledSource}
          shouldOverlayBeVisible={shouldOverlayBeVisible}
        />
      ) : (
        <div
          className={cn("my-8 flex flex-col items-center rounded-sm p-3", {
            "text-secondary": shouldOverlayBeVisible,
            "text-danger-secondary": isDropDisabled,
          })}
        >
          {dropErrorMessage ? (
            <div className="flex items-center">
              <WarningCircleOutline width={13} height={13} /> &nbsp;
              <span>
                {dropErrorMessage === COMPLETED_CYCLE_DROP_ERROR && t("issue_ui.cannot_move_to_completed_cycle")}
                {dropErrorMessage === DATE_BUCKET_DROP_ERROR && t("issue.dates.bucket.no_single_date")}
                {dropErrorMessage === DATE_BUCKET_NO_DAY_LEFT_ERROR && t("issue.dates.bucket.no_day_left")}
                {dropErrorMessage !== COMPLETED_CYCLE_DROP_ERROR &&
                  dropErrorMessage !== DATE_BUCKET_DROP_ERROR &&
                  dropErrorMessage !== DATE_BUCKET_NO_DAY_LEFT_ERROR &&
                  dropErrorMessage}
              </span>
            </div>
          ) : (
            <>
              {readableOrderBy && (
                <span>
                  {t("issue.layouts.ordered_by_label")} <span className="font-semibold">{t(readableOrderBy)}</span>.
                </span>
              )}
              <span>{t("entity.drop_here_to_move", { entity: isEpic ? "epic" : "work item" })}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
