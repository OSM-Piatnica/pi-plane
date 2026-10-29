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
      {/* react-doctor-disable-next-line no-static-element-interactions -- mouse-drag handle; resizing a timeline block has no keyboard equivalent yet */}
      <div // oxlint-disable-line jsx-a11y/no-static-element-interactions -- mouse-drag handle (see above)
        onMouseDown={(e) => {
          handleBlockDrag(e, "left");
        }}
        // react-doctor-disable-next-line mouse-events-have-key-events -- hover only shows the date label; mouse-drag handle; resizing a timeline block has no keyboard equivalent yet
        onMouseOver={() => {
          // oxlint-disable-line jsx-a11y/mouse-events-have-key-events -- hover label only
          setIsHovering(true);
        }}
        // react-doctor-disable-next-line mouse-events-have-key-events -- hover only shows the date label; mouse-drag handle; resizing a timeline block has no keyboard equivalent yet
        onMouseOut={() => {
          // oxlint-disable-line jsx-a11y/mouse-events-have-key-events -- hover label only
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
