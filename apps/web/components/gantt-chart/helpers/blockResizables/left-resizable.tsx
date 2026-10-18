/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane utils
import { cn } from "@plane/utils";
//helpers
//
//hooks
import { useLocalizedDates } from "@/hooks/use-localized-dates";
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";

type LeftResizableProps = {
  enableBlockLeftResize: boolean;
  handleBlockDrag: (e: React.MouseEvent<HTMLDivElement, MouseEvent>, dragDirection: "left" | "right" | "move") => void;
  isMoving: "left" | "right" | "move" | undefined;
  position?: {
    marginLeft: number;
    width: number;
  };
};
export const LeftResizable = observer(function LeftResizable(props: LeftResizableProps) {
  const { enableBlockLeftResize, isMoving, handleBlockDrag, position } = props;
  const [isHovering, setIsHovering] = useState(false);

  const { formatDate } = useLocalizedDates();
  const { getDateFromPositionOnGantt } = useTimeLineChartStore();

  const date = position ? getDateFromPositionOnGantt(position.marginLeft, 0) : undefined;
  const dateString = date ? formatDate(date) : undefined;

  const isLeftResizing = isMoving === "left" || isMoving === "move";

  if (!enableBlockLeftResize) return null;

  return (
    <>
      {(isHovering || isLeftResizing) && dateString && (
        <div className="absolute -left-36 flex h-full w-32 items-center justify-end text-11 font-regular text-tertiary">
          <div className="rounded-sm bg-accent-subtle px-2 py-1">{dateString}</div>
        </div>
      )}
      {/* oxlint-disable-next-line jsx-a11y/no-static-element-interactions -- behaviour-preserving lint cleanup; a11y handled separately */}
      <div
        onMouseDown={(e) => {
          handleBlockDrag(e, "left");
        }}
        // oxlint-disable-next-line jsx-a11y/mouse-events-have-key-events -- behaviour-preserving lint cleanup; a11y handled separately
        onMouseOver={() => {
          setIsHovering(true);
        }}
        // oxlint-disable-next-line jsx-a11y/mouse-events-have-key-events -- behaviour-preserving lint cleanup; a11y handled separately
        onMouseOut={() => {
          setIsHovering(false);
        }}
        className="absolute top-1/2 -left-1.5 z-[6] h-full w-3 -translate-y-1/2 cursor-col-resize rounded-md"
      />
      <div
        className={cn(
          "absolute top-1/2 left-1 z-[5] h-7 w-1 -translate-y-1/2 rounded-xs bg-surface-1 opacity-0 transition-all duration-300 group-hover:opacity-100",
          {
            "-left-1.5 opacity-100": isLeftResizing,
          }
        )}
      />
    </>
  );
});
