/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TRelationRescheduleShift } from "@plane/types";
import { getRescheduleDeadlineWarning } from "@/components/workflow/reschedule-deadline-warning";

const shift = (overrides: Partial<TRelationRescheduleShift> = {}): TRelationRescheduleShift => ({
  id: "i41",
  project_id: "p1",
  sequence_id: 41,
  ref: "DEMO-41",
  name: "Print run",
  start_date: "2026-11-02",
  finish_date: "2026-11-04",
  new_start_date: "2026-11-05",
  new_finish_date: "2026-11-09",
  target_date: "2026-11-04",
  deadline_overrun_days: null,
  previous_deadline_overrun_days: null,
  ...overrides,
});

describe("getRescheduleDeadlineWarning", () => {
  it("warns with the overrun the API sends", () => {
    expect(getRescheduleDeadlineWarning(shift({ deadline_overrun_days: 3 }))).toEqual({
      key: "issue.relation.reschedule.deadline_overrun",
      params: { issue: "DEMO-41", count: 3 },
    });
  });

  it("names the overrun an item had already", () => {
    expect(
      getRescheduleDeadlineWarning(shift({ deadline_overrun_days: 4, previous_deadline_overrun_days: 1 }))
    ).toEqual({
      key: "issue.relation.reschedule.deadline_overrun_more",
      params: { issue: "DEMO-41", count: 4, previous: 1 },
    });
  });

  it("stays silent without an overrun, also for an API without the field", () => {
    expect(getRescheduleDeadlineWarning(shift())).toBeNull();
    expect(getRescheduleDeadlineWarning(shift({ deadline_overrun_days: 0 }))).toBeNull();
    const { deadline_overrun_days: _omitted, ...older } = shift();
    expect(getRescheduleDeadlineWarning(older)).toBeNull();
  });
});
