/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  getDepartmentLabel,
  getMovedSortOrder,
  isDepartmentColor,
  normalizeDepartmentCode,
  parseDepartmentList,
  planDepartmentImport,
  sortDepartments,
} from "@/helpers/department";

describe("parseDepartmentList", () => {
  it("reads one CODE;Name per line and passes over empty lines", () => {
    const { rows, skipped } = parseDepartmentList("RM;Marketing\n\n  qa ; Quality assurance \r\nIT\tIT services\n");
    expect(rows).toEqual([
      { code: "RM", name: "Marketing" },
      { code: "QA", name: "Quality assurance" },
      { code: "IT", name: "IT services" },
    ]);
    expect(skipped).toEqual([]);
  });

  it("takes a line without a separator as a department without a code", () => {
    expect(parseDepartmentList("Research, Development").rows).toEqual([{ code: "", name: "Research, Development" }]);
  });

  it("keeps further separators in the name", () => {
    expect(parseDepartmentList("PR;Press; media").rows).toEqual([{ code: "PR", name: "Press; media" }]);
  });

  it("reports the lines it cannot use with their numbers", () => {
    const text = ["RM;Marketing", "QA;", "rm;Other", "XX;marketing", `${"A".repeat(17)};Long code`].join("\n");
    const { rows, skipped } = parseDepartmentList(text);
    expect(rows).toEqual([{ code: "RM", name: "Marketing" }]);
    expect(skipped.map(({ line, problem }) => [line, problem])).toEqual([
      [2, "empty_name"],
      [3, "duplicate"],
      [4, "duplicate"],
      [5, "code_too_long"],
    ]);
  });

  it("refuses a name longer than a group name can be", () => {
    expect(parseDepartmentList(`LN;${"n".repeat(256)}`).skipped[0]?.problem).toBe("name_too_long");
  });

  it("returns nothing for an empty text", () => {
    expect(parseDepartmentList("  \n ")).toEqual({ rows: [], skipped: [] });
  });
});

describe("planDepartmentImport", () => {
  const groups = [
    { name: "Marketing", code: "RM", kind: "department" as const, parent: null },
    { name: "Sales", code: "SL", kind: "group" as const, parent: null },
    { name: "Poland", code: "", kind: "group" as const, parent: "p1" },
  ];

  it("leaves out the departments whose code or top-level name is already there", () => {
    const plan = planDepartmentImport(
      [
        { code: "RM", name: "Brand" },
        { code: "XX", name: "sales" },
        { code: "SL", name: "Selling" },
        { code: "", name: "Poland" },
      ],
      groups
    );
    // a plain group does not hold a code, and a nested group does not hold a top-level name
    expect(plan.create).toEqual([
      { code: "SL", name: "Selling" },
      { code: "", name: "Poland" },
    ]);
    expect(plan.existing).toEqual([
      { code: "RM", name: "Brand" },
      { code: "XX", name: "sales" },
    ]);
  });
});

describe("sortDepartments and getMovedSortOrder", () => {
  const list = [
    { id: "c", name: "C", sort_order: 30000 },
    { id: "a", name: "A", sort_order: 10000 },
    { id: "b2", name: "Beta", sort_order: 20000 },
    { id: "b1", name: "Alpha", sort_order: 20000 },
  ];

  it("orders by place, then by name, without changing the given list", () => {
    expect(sortDepartments(list).map((department) => department.id)).toEqual(["a", "b1", "b2", "c"]);
    expect(list[0]?.id).toBe("c");
  });

  it("puts a moved department between its new neighbours", () => {
    const sorted = [
      { id: "a", sort_order: 10000 },
      { id: "b", sort_order: 20000 },
      { id: "c", sort_order: 40000 },
    ];
    expect(getMovedSortOrder(sorted, "c", -1)).toBe(15000);
    expect(getMovedSortOrder(sorted, "a", 1)).toBe(30000);
    // past the first or the last one
    expect(getMovedSortOrder(sorted, "b", -1)).toBe(0);
    expect(getMovedSortOrder(sorted, "b", 1)).toBe(50000);
  });

  it("does not move past the ends, or a department that is not in the list", () => {
    const sorted = [
      { id: "a", sort_order: 1 },
      { id: "b", sort_order: 2 },
    ];
    expect(getMovedSortOrder(sorted, "a", -1)).toBeNull();
    expect(getMovedSortOrder(sorted, "b", 1)).toBeNull();
    expect(getMovedSortOrder(sorted, "x", 1)).toBeNull();
  });
});

describe("small helpers", () => {
  it("normalises codes like the server", () => {
    expect(normalizeDepartmentCode("  rm ")).toBe("RM");
  });

  it("accepts hex colours and no colour", () => {
    for (const color of ["", "#fff", "#3F76ff", "#3f76ffaa"]) expect(isDepartmentColor(color)).toBe(true);
    for (const color of ["red", "3f76ff", "#12", "#12345"]) expect(isDepartmentColor(color)).toBe(false);
  });

  it("labels a department with its code when it has one", () => {
    expect(getDepartmentLabel({ name: "Marketing", code: "RM" })).toBe("RM · Marketing");
    expect(getDepartmentLabel({ name: "Marketing", code: "" })).toBe("Marketing");
  });
});
