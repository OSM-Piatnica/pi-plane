/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getProjectFormValues } from "@/components/projects/create/utils";

describe("getProjectFormValues", () => {
  it("starts a new project with modules and views on and pages off", () => {
    const values = getProjectFormValues();
    expect(values.module_view).toBe(true);
    expect(values.issue_views_view).toBe(true);
    expect(values.page_view).toBe(false);
  });

  it("leaves the other features as they were", () => {
    const values = getProjectFormValues();
    expect(values.cycle_view).toBe(false);
    expect(values.inbox_view).toBe(false);
    expect(values.is_time_tracking_enabled).toBe(false);
    expect(values.is_issue_type_enabled).toBe(false);
  });
});
