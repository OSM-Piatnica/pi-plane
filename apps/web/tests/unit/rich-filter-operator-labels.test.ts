/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { DATE_OPERATOR_LABELS_MAP, OPERATOR_LABELS_MAP, OPERATOR_LABEL_KEY_PREFIX } from "@plane/constants";
import { translateOperatorLabel } from "../../helpers/rich-filter-operator-label";

const locales = resolve(import.meta.dirname, "../../../../packages/i18n/src/locales");
const english = JSON.parse(readFileSync(resolve(locales, "en/project.json"), "utf8")) as {
  project_components: { rich_filters: { operators: Record<string, string> } };
};
const operators = english.project_components.rich_filters.operators;
const keysOf = (labels: Record<string, string>) =>
  Object.values(labels).map((label) => label.slice(OPERATOR_LABEL_KEY_PREFIX.length));

describe("operator labels", () => {
  it("are translation keys that exist in the English locale", () => {
    for (const label of [...Object.values(OPERATOR_LABELS_MAP), ...Object.values(DATE_OPERATOR_LABELS_MAP)]) {
      expect(label.startsWith(OPERATOR_LABEL_KEY_PREFIX), label).toBe(true);
    }
    for (const key of [...keysOf(OPERATOR_LABELS_MAP), ...keysOf(DATE_OPERATOR_LABELS_MAP)]) {
      expect(operators[key], key).toBeTypeOf("string");
    }
  });

  it("read as the operators did before they were translated", () => {
    expect(operators).toEqual({
      exact: "is",
      in: "is any of",
      range: "between",
      not_exact: "is not",
      not_in: "is none of",
      not_range: "not between",
    });
  });

  it("exist in every locale", () => {
    for (const locale of ["bg", "de", "fr", "pl", "ru", "ua", "ja", "zh-CN", "pl-x-podlaski"]) {
      const translated = JSON.parse(readFileSync(resolve(locales, locale, "project.json"), "utf8")).project_components
        .rich_filters.operators as Record<string, string>;
      expect(Object.keys(translated).toSorted(), locale).toEqual(Object.keys(operators).toSorted());
      expect(Object.values(translated).every(Boolean), locale).toBe(true);
    }
  });
});

describe("translateOperatorLabel", () => {
  const t = (key: string) => `[${key.slice(OPERATOR_LABEL_KEY_PREFIX.length)}]`;

  it("translates an operator label and leaves other text as it is", () => {
    expect(translateOperatorLabel(t, OPERATOR_LABELS_MAP.not_in)).toBe("[not_in]");
    expect(translateOperatorLabel(t, "--")).toBe("--");
    expect(translateOperatorLabel(t, "starts with")).toBe("starts with");
  });
});
