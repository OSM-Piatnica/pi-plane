/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { RefObject } from "react";
import { useRef } from "react";
import { observer } from "mobx-react";
// components
import type { IBlockUpdateDependencyData, IGanttBlock } from "@plane/types";
import { EGanttBlockType } from "@plane/types";
import { cn } from "@plane/utils";
import RenderIfVisible from "@/components/core/render-if-visible-HOC";
// helpers
// hooks
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";
// constants
import { BLOCK_HEIGHT } from "../constants";
// components
import { ChartDraggable } from "../helpers";
import { GanttDueMarker } from "./due-marker";
import { useGanttResizable } from "../helpers/blockResizables/use-gantt-resizable";
import { getBlockChartDates, isBlockOnChart, isBlockRolledUp } from "../views/helpers";
import { GanttRollupBracket } from "./rollup-bracket";

type TBarEditing = { enableBlockLeftResize: boolean; enableBlockRightResize: boolean; enableBlockMove: boolean };

/**
 * How a block shows on the chart, and what of it can be dragged: a bar drawn from the children's dates (rolled up)
 * has nothing of its own to drag, and a dated parent gets a bracket spanning its children.
 */
const getBarState = (block: IGanttBlock | undefined, editing: TBarEditing) => {
  const isOnChart = isBlockOnChart(block);
  const isRolledUp = isBlockRolledUp(block);
  const chartDates = block ? getBlockChartDates(block) : undefined;
  const isComplete = !!chartDates?.start_date && !!chartDates?.target_date;
  // a work item with only a start or only a finish is a one day marker: movable, but never resizable
  const isSingleEndedWorkItem =
    block?.meta?.type === EGanttBlockType.ISSUE && !!chartDates?.start_date !== !!chartDates?.target_date;
  return {
    isOnChart,
    isSingleEndedWorkItem,
    canResizeLeft: editing.enableBlockLeftResize && !isRolledUp && !isSingleEndedWorkItem,
    canResizeRight: editing.enableBlockRightResize && !isRolledUp && !isSingleEndedWorkItem,
    canMove: editing.enableBlockMove && (isComplete || isSingleEndedWorkItem) && !isRolledUp,
    showRollupBracket: isOnChart && !isRolledUp && !!block?.rollup?.position,
  };
};

type Props = {
  blockId: string;
  showAllBlocks: boolean;
  blockToRender: (data: any) => React.ReactNode;
  enableBlockLeftResize: boolean;
  enableBlockRightResize: boolean;
  enableBlockMove: boolean;
  enableDependency: boolean;
  ganttContainerRef: RefObject<HTMLDivElement | null>;
  updateBlockDates?: (updates: IBlockUpdateDependencyData[]) => Promise<void>;
};

export const GanttChartBlock = observer(function GanttChartBlock(props: Props) {
  const {
    blockId,
    showAllBlocks,
    blockToRender,
    enableBlockLeftResize,
    enableBlockRightResize,
    enableBlockMove,
    ganttContainerRef,
    enableDependency,
    updateBlockDates,
  } = props;
  // store hooks
  const { updateActiveBlockId, getBlockById, getIsCurrentDependencyDragging, currentView } = useTimeLineChartStore();
  // refs
  const resizableRef = useRef<HTMLDivElement>(null);

  const block = getBlockById(blockId);

  const isCurrentDependencyDragging = getIsCurrentDependencyDragging(blockId);

  const { isMoving, handleBlockDrag } = useGanttResizable(block, resizableRef, ganttContainerRef, updateBlockDates);

  const bar = getBarState(block, { enableBlockLeftResize, enableBlockRightResize, enableBlockMove });
  const isBlockVisibleOnChart = bar.isOnChart;
  const isDueMarkerShown = block?.meta?.type === EGanttBlockType.ISSUE && !!block?.due_date;

  // hide the block if it doesn't have start and target dates and showAllBlocks is false
  if (!block || (!showAllBlocks && !isBlockVisibleOnChart)) return null;

  if (!block.data) return null;

  return (
    <div
      className={cn("relative z-[5]", {
        "transition-all": !!isMoving && currentView === "week",
        "pointer-events-none": !isBlockVisibleOnChart,
      })}
      id={`gantt-block-${block.id}`}
      ref={resizableRef}
      style={{
        height: `${BLOCK_HEIGHT}px`,
        marginLeft: `${block.position?.marginLeft}px`,
        width: `${block.position?.width}px`,
      }}
    >
      {isBlockVisibleOnChart && (
        <RenderIfVisible
          root={ganttContainerRef}
          horizontalOffset={100}
          verticalOffset={200}
          classNames="flex h-full w-full items-center"
          placeholderChildren={<div className="h-8 w-full rounded-sm bg-layer-1" />}
          shouldRecordHeights={false}
          forceRender={isCurrentDependencyDragging}
        >
          <div
            className={cn("relative h-full w-full")}
            onMouseEnter={() => updateActiveBlockId(blockId)}
            onMouseLeave={() => updateActiveBlockId(null)}
          >
            <ChartDraggable
              block={block}
              blockToRender={blockToRender}
              handleBlockDrag={handleBlockDrag}
              enableBlockLeftResize={bar.canResizeLeft}
              enableBlockRightResize={bar.canResizeRight}
              enableBlockMove={bar.canMove}
              enableDependency={enableDependency}
              isMoving={isMoving}
              ganttContainerRef={ganttContainerRef}
            />
          </div>
        </RenderIfVisible>
      )}
      {isDueMarkerShown && (
        <GanttDueMarker
          block={block}
          ganttContainerRef={ganttContainerRef}
          parentOffset={block.position?.marginLeft ?? 0}
          enableMove={enableBlockMove}
          updateBlockDates={updateBlockDates}
        />
      )}
      {bar.showRollupBracket && <GanttRollupBracket block={block} />}
    </div>
  );
});
