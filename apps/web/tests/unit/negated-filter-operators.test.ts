/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { DATE_OPERATOR_LABELS_MAP, OPERATOR_LABELS_MAP } from "@plane/constants";
import { workItemFiltersAdapter } from "@plane/shared-state";
import type { TFilterExpression, TWorkItemFilterProperty } from "@plane/types";
import {
  createAndGroupNode,
  createConditionNode,
  deepCompareFilterExpressions,
  extractConditionsWithDisplayOperators,
  getOperatorForDisplay,
  getOperatorForPayload,
  isNegatedOperator,
} from "@plane/utils";

const state = (operator: "exact" | "in", value: string | string[], isNegation?: boolean) =>
  createConditionNode({ property: "state_id", operator, value, isNegation });

describe("operators of a negated condition", () => {
  it("are shown with a not_ prefix and stored as the positive operator plus a flag", () => {
    expect(getOperatorForDisplay("in", true)).toBe("not_in");
    expect(getOperatorForDisplay("in", false)).toBe("in");
    expect(getOperatorForDisplay("exact")).toBe("exact");
    expect(getOperatorForPayload("not_in")).toEqual({ operator: "in", isNegation: true });
    expect(getOperatorForPayload("exact")).toEqual({ operator: "exact", isNegation: false });
    expect(getOperatorForPayload(getOperatorForDisplay("range", true))).toEqual({
      operator: "range",
      isNegation: true,
    });
  });

  it("are recognised by the prefix", () => {
    expect(isNegatedOperator("not_exact")).toBe(true);
    expect(isNegatedOperator("exact")).toBe(false);
  });

  it("have a label each", () => {
    expect(OPERATOR_LABELS_MAP.not_exact).toBe("is not");
    expect(OPERATOR_LABELS_MAP.not_in).toBe("is none of");
    expect(OPERATOR_LABELS_MAP.not_range).toBe("not between");
    expect(DATE_OPERATOR_LABELS_MAP.not_exact).toBe("is not");
    expect(DATE_OPERATOR_LABELS_MAP.not_range).toBe("not between");
  });

  it("are listed with the negation of the conditions of an expression", () => {
    const expression = createAndGroupNode([state("in", ["a", "b"], true), state("exact", "c")]);
    expect(extractConditionsWithDisplayOperators(expression).map((condition) => condition.operator)).toEqual([
      "not_in",
      "exact",
    ]);
  });
});

describe("the work item filter adapter with a negated condition", () => {
  it("reads { not: condition } as a negated condition", () => {
    const internal = workItemFiltersAdapter.toInternal({ not: { state_id__in: "a,b" } });
    expect(internal).toMatchObject({ property: "state_id", operator: "in", value: ["a", "b"], isNegation: true });
  });

  it("writes a negated condition back as { not: condition }", () => {
    expect(workItemFiltersAdapter.toExternal(state("in", ["a", "b"], true))).toEqual({
      not: { state_id__in: "a,b" },
    });
    expect(workItemFiltersAdapter.toExternal(state("in", ["a", "b"]))).toEqual({ state_id__in: "a,b" });
  });

  it("round-trips negated and plain conditions inside a group", () => {
    const external = { and: [{ state_id__in: "a,b" }, { not: { priority__in: "urgent" } }] };
    const internal = workItemFiltersAdapter.toInternal(external) as TFilterExpression<TWorkItemFilterProperty>;
    expect(workItemFiltersAdapter.toExternal(internal)).toEqual(external);
  });
});

describe("comparing expressions", () => {
  it("tells a negated condition from the same condition without negation", () => {
    expect(deepCompareFilterExpressions(state("in", ["a"], true), state("in", ["a"], false))).toBe(false);
    expect(deepCompareFilterExpressions(state("in", ["a"], true), state("in", ["a"], true))).toBe(true);
    // an unset flag is no negation
    expect(deepCompareFilterExpressions(state("in", ["a"]), state("in", ["a"], false))).toBe(true);
  });
});
