/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  buildDependencyPathD,
  buildGanttDependencyEdges,
  getDependencyAnchorSides,
  getDependencyArrowEndpoints,
  isDependencyRelationInvalid,
  wouldUpdatesViolateDependencies,
} from "../../helpers/gantt-dependency-helpers";

describe("gantt-dependency-helpers", () => {
  it("flags blocking when predecessor finishes after successor starts", () => {
    expect(
      isDependencyRelationInvalid(
        "blocking",
        { start_date: "2026-01-01", target_date: "2026-01-10" },
        { start_date: "2026-01-05", target_date: "2026-01-20" }
      )
    ).toBe(true);
  });

  it("allows valid finish_before relation", () => {
    expect(
      isDependencyRelationInvalid(
        "finish_before",
        { start_date: "2026-01-01", target_date: "2026-01-04" },
        { start_date: "2026-01-05", target_date: "2026-01-20" }
      )
    ).toBe(false);
  });

  it("flags blocking when predecessor ends on the same day successor starts", () => {
    expect(
      isDependencyRelationInvalid(
        "blocking",
        { start_date: "2026-01-01", target_date: "2026-01-05" },
        { start_date: "2026-01-05", target_date: "2026-01-20" }
      )
    ).toBe(true);
  });

  it("treats datetime payloads by calendar day", () => {
    expect(
      isDependencyRelationInvalid(
        "blocking",
        { start_date: "2026-01-01", target_date: "2026-01-10T00:00:00Z" },
        { start_date: "2026-01-05T12:00:00Z", target_date: "2026-01-20" }
      )
    ).toBe(true);
  });

  it("builds edges for visible dependency relations", () => {
    const edges = buildGanttDependencyEdges(
      ["a", "b"],
      {
        a: { blocking: ["b"] },
      },
      (id) =>
        id === "a"
          ? { start_date: "2026-01-01", target_date: "2026-01-10" }
          : { start_date: "2026-01-05", target_date: "2026-01-20" }
    );
    expect(edges).toHaveLength(1);
    expect(edges[0].sourceId).toBe("a");
    expect(edges[0].targetId).toBe("b");
    expect(edges[0].isInvalid).toBe(true);
  });

  it("detects date updates that violate dependencies", () => {
    const violated = wouldUpdatesViolateDependencies(
      [{ id: "a", target_date: "2026-01-12" }],
      {
        a: { blocking: ["b"] },
      },
      (id) =>
        id === "a"
          ? { start_date: "2026-01-01", target_date: "2026-01-04" }
          : { start_date: "2026-01-05", target_date: "2026-01-20" }
    );
    expect(violated).toBe(true);
  });

  describe("lag", () => {
    const dates = (id: string) =>
      id === "a"
        ? { start_date: "2026-01-01", target_date: "2026-01-10" }
        : { start_date: "2026-01-11", target_date: "2026-01-20" };

    it("is part of the check when edges are built", () => {
      const withoutLag = buildGanttDependencyEdges(["a", "b"], { a: { blocking: ["b"] } }, dates);
      const withLag = buildGanttDependencyEdges(["a", "b"], { a: { blocking: ["b"] } }, dates, () => 2);
      expect(withoutLag[0].isInvalid).toBe(false);
      expect(withLag[0].isInvalid).toBe(true);
    });

    it("asks the lag of the relation as seen from the work item that owns it", () => {
      const asked: string[] = [];
      buildGanttDependencyEdges(["a", "b"], { a: { blocking: ["b"] } }, dates, (issueId, type, relatedId) => {
        asked.push(`${issueId}:${type}:${relatedId}`);
        return 0;
      });
      expect(asked).toEqual(["a:blocking:b"]);
    });

    it("makes a drag that breaks a lag count as a violation", () => {
      const updates = [{ id: "b", start_date: "2026-01-12" }];
      const relationMap = { a: { blocking: ["b"] }, b: { blocked_by: ["a"] } };
      expect(wouldUpdatesViolateDependencies(updates, relationMap, dates)).toBe(false);
      expect(wouldUpdatesViolateDependencies(updates, relationMap, dates, () => 2)).toBe(true);
    });
  });

  it("draws start-to-finish arrows from the item that starts to the one that finishes", () => {
    expect(getDependencyArrowEndpoints("start_before_finish", "a", "b")).toEqual({ fromId: "a", toId: "b" });
    expect(getDependencyArrowEndpoints("finish_after_start", "b", "a")).toEqual({ fromId: "a", toId: "b" });
  });

  describe("arrow anchors", () => {
    it("joins the edges of the bars a project plan would", () => {
      expect(getDependencyAnchorSides("blocked_by")).toEqual({ from: "right", to: "left" });
      expect(getDependencyAnchorSides("blocking")).toEqual({ from: "right", to: "left" });
      expect(getDependencyAnchorSides("start_before")).toEqual({ from: "left", to: "left" });
      expect(getDependencyAnchorSides("start_after")).toEqual({ from: "left", to: "left" });
      expect(getDependencyAnchorSides("finish_before")).toEqual({ from: "right", to: "right" });
      expect(getDependencyAnchorSides("finish_after")).toEqual({ from: "right", to: "right" });
      expect(getDependencyAnchorSides("start_before_finish")).toEqual({ from: "left", to: "right" });
      expect(getDependencyAnchorSides("finish_after_start")).toEqual({ from: "left", to: "right" });
    });

    it("bends the curve away from the bar it leaves and towards the side it arrives at", () => {
      // from the end of a bar to the start of the next: the usual shape
      expect(buildDependencyPathD(100, 10, 200, 40)).toBe("M 100 10 C 140 10, 160 40, 200 40");
      // start to finish, the target further left: leaves to the left, arrives from the right
      expect(buildDependencyPathD(300, 10, 100, 40, "left", "right")).toBe("M 300 10 C 220 10, 180 40, 100 40");
    });
  });
});
