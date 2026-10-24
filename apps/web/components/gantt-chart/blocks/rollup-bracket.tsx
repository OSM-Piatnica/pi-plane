/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the timeline of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
import type { IGanttBlock } from "@plane/types";
import { renderFormattedDate } from "@plane/utils";

type Props = {
  block: IGanttBlock;
};

/**
 * A summary bracket under a parent's own bar that spans the work items below it, in the style of project-plan
 * summary tasks. Where the children start before or end after the parent's own dates, that part of the bracket turns
 * red.
 */
export const GanttRollupBracket = observer(function GanttRollupBracket(props: Props) {
  const { block } = props;
  const { t } = useTranslation();

  const rollup = block.rollup;
  if (!rollup?.position || !block.position) return null;

  // offsets relative to the parent's own bar, which positions this element
  const left = rollup.position.marginLeft - block.position.marginLeft;
  const width = rollup.position.width;
  const overrunStart = Math.max(0, -left);
  const overrunEnd = Math.max(0, left + width - block.position.width);

  const lines = [
    t("timeline_rollup.children_span", {
      start: renderFormattedDate(rollup.start_date ?? rollup.target_date) ?? "",
      end: renderFormattedDate(rollup.target_date ?? rollup.start_date) ?? "",
    }),
  ];
  if (overrunStart > 0) lines.push(t("timeline_rollup.starts_early"));
  if (overrunEnd > 0) lines.push(t("timeline_rollup.ends_late"));

  return (
    // the overrun shows in red on the bracket itself; the tooltip says what it means
    <Tooltip label={lines.join(" · ")} layout="stacked">
      <div
        className="absolute bottom-0.5 z-[4] h-1.5 rounded-b-sm border-x-2 border-b-2 border-strong"
        style={{ left: `${left}px`, width: `${width}px` }}
        data-testid="gantt-rollup-bracket"
      >
        {overrunStart > 0 && (
          <div
            className="absolute -bottom-0.5 -left-0.5 h-1.5 rounded-bl-sm border-b-2 border-l-2 border-danger-strong"
            style={{ width: `${overrunStart + 2}px` }}
          />
        )}
        {overrunEnd > 0 && (
          <div
            className="absolute -right-0.5 -bottom-0.5 h-1.5 rounded-br-sm border-r-2 border-b-2 border-danger-strong"
            style={{ width: `${overrunEnd + 2}px` }}
          />
        )}
      </div>
    </Tooltip>
  );
});
