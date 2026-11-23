/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { workItemFiltersAdapter } from "@plane/shared-state";
import type { TFilterExpression, TWorkItemFilterProperty } from "@plane/types";
import { FILTER_FIELD_TYPE, WORK_ITEM_FILTER_PROPERTY_KEYS } from "@plane/types";
import { createConditionNode, getCriticalPathFilterConfig } from "@plane/utils";

const config = (isEnabled = true) =>
  getCriticalPathFilterConfig<TWorkItemFilterProperty>("is_critical")({
    isEnabled,
    allowedOperators: new Set(["exact", "in", "range"]),
    allowNegative: false,
  });

type TWithOptions = { type?: string; getOptions?: unknown };

/** The options of an operator's select, which the operator types only know in some of their variants. */
const optionsOf = (operator: unknown) => {
  const { getOptions } = (operator ?? {}) as TWithOptions;
  return typeof getOptions === "function" ? (getOptions as () => unknown)() : getOptions;
};

describe("the critical path filter", () => {
  it("is a work item filter that only the pages of one project offer", () => {
    expect(WORK_ITEM_FILTER_PROPERTY_KEYS).toContain("is_critical");
    expect(ISSUE_DISPLAY_FILTERS_BY_PAGE.issues.filters).toContain("is_critical");
    // workspace views, the profile and the archive mix projects (or have no schedule), so they do not
    expect(ISSUE_DISPLAY_FILTERS_BY_PAGE.my_issues.filters).not.toContain("is_critical");
    expect(ISSUE_DISPLAY_FILTERS_BY_PAGE.profile_issues.filters).not.toContain("is_critical");
    expect(ISSUE_DISPLAY_FILTERS_BY_PAGE.archived_issues.filters).not.toContain("is_critical");
  });

  it("asks yes or no with the single operator `exact`", () => {
    const filter = config();
    expect(filter.id).toBe("is_critical");
    expect([...filter.supportedOperatorConfigsMap.keys()]).toEqual(["exact"]);
    const operator = filter.supportedOperatorConfigsMap.get("exact");
    expect(operator?.type).toBe(FILTER_FIELD_TYPE.SINGLE_SELECT);
    const options = optionsOf(operator);
    expect(options).toEqual([
      expect.objectContaining({ id: "true", value: "true", label: "Yes" }),
      expect.objectContaining({ id: "false", value: "false", label: "No" }),
    ]);
  });

  it("translates the labels when it is given a translator", () => {
    const filter = getCriticalPathFilterConfig<TWorkItemFilterProperty>("is_critical")({
      isEnabled: true,
      allowedOperators: new Set(["exact"]),
      t: (key) => `<${key}>`,
    });
    expect(filter.label).toBe("<schedule_analysis.critical_path>");
    const operator = filter.supportedOperatorConfigsMap.get("exact");
    const options = optionsOf(operator);
    expect(options).toEqual([expect.objectContaining({ label: "<yes>" }), expect.objectContaining({ label: "<no>" })]);
  });

  it("goes to the API as is_critical__exact and comes back", () => {
    const node = createConditionNode({ property: "is_critical", operator: "exact", value: "true" });
    expect(workItemFiltersAdapter.toExternal(node)).toEqual({ is_critical__exact: "true" });
    const internal = workItemFiltersAdapter.toInternal({
      is_critical__exact: "false",
    }) as TFilterExpression<TWorkItemFilterProperty>;
    expect(workItemFiltersAdapter.toExternal(internal)).toEqual({ is_critical__exact: "false" });
  });
});
