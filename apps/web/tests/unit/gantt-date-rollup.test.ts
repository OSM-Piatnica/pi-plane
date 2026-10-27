/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { IGanttBlock, TGanttDateRollup } from "@plane/types";
import { getBlockChartDates, isBlockOnChart, isBlockRolledUp } from "../../components/gantt-chart/views/helpers";
import { BaseTimeLineStore } from "../../store/timeline/base-timeline.store";

const block = (start?: string, target?: string): IGanttBlock => ({
  data: {},
  id: "a",
  name: "A",
  sort_order: undefined,
  start_date: start,
  target_date: target,
});

const rollup = (start: string | null, target: string | null): TGanttDateRollup => ({
  start_date: start,
  target_date: target,
  children_count: 2,
  descendants_count: 3,
});

// buildBlockRollup only reads its arguments, so it can run without a root store
const build = (own: IGanttBlock, children: TGanttDateRollup) =>
  BaseTimeLineStore.prototype.buildBlockRollup.call({}, own, children);

describe("buildBlockRollup", () => {
  it("keeps the own dates and only brackets the children when the block is dated", () => {
    const result = build(block("2026-02-01", "2026-02-10"), rollup("2026-01-15", "2026-02-20"));
    expect(result.is_start_inferred).toBe(false);
    expect(result.is_target_inferred).toBe(false);
  });

  it("takes the missing sides from the children", () => {
    const result = build(block(), rollup("2026-01-15", "2026-02-20"));
    expect(result.is_start_inferred).toBe(true);
    expect(result.is_target_inferred).toBe(true);
  });

  it("does not infer a side that would put the end before the start", () => {
    // only a start of its own, and the children all end earlier
    expect(build(block("2026-03-01"), rollup("2026-01-01", "2026-02-01")).is_target_inferred).toBe(false);
    // only an end of its own, and the children all start later
    expect(build(block(), rollup("2026-05-01", "2026-06-01")).is_start_inferred).toBe(true);
    expect(build(block(undefined, "2026-03-01"), rollup("2026-05-01", "2026-06-01")).is_start_inferred).toBe(false);
  });

  it("infers nothing from children without dates", () => {
    const result = build(block(), rollup(null, null));
    expect(result.is_start_inferred || result.is_target_inferred).toBe(false);
  });
});

describe("chart dates of a block", () => {
  it("are the own dates, completed from the children where they were inferred", () => {
    const own = block("2026-02-01");
    own.rollup = { ...rollup("2026-01-15", "2026-02-20"), is_start_inferred: false, is_target_inferred: true };
    expect(getBlockChartDates(own)).toEqual({ start_date: "2026-02-01", target_date: "2026-02-20" });
    expect(isBlockRolledUp(own)).toBe(true);
  });

  it("put a block on the chart only when it has a date of its own or an inferred one", () => {
    expect(isBlockOnChart(undefined)).toBe(false);
    expect(isBlockOnChart(block())).toBe(false);
    expect(isBlockOnChart(block("2026-02-01"))).toBe(true);
    const parent = block();
    parent.rollup = { ...rollup("2026-01-15", "2026-02-20"), is_start_inferred: true, is_target_inferred: true };
    expect(isBlockOnChart(parent)).toBe(true);
    expect(isBlockRolledUp(parent)).toBe(true);
    expect(isBlockRolledUp(block("2026-02-01"))).toBe(false);
  });
});
