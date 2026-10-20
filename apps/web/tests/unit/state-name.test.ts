/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getStateName } from "../../helpers/state-name";

const t = (key: string) => `[${key}]`;

describe("getStateName", () => {
  it("translates the default state names, including both spellings of To do", () => {
    expect(getStateName("Backlog", t)).toBe("[default_state_names.backlog]");
    expect(getStateName("Todo", t)).toBe("[default_state_names.todo]");
    expect(getStateName("To do", t)).toBe("[default_state_names.todo]");
    expect(getStateName("In Progress", t)).toBe("[default_state_names.in_progress]");
    expect(getStateName("Done", t)).toBe("[default_state_names.done]");
    expect(getStateName("Cancelled", t)).toBe("[default_state_names.cancelled]");
    expect(getStateName("Triage", t)).toBe("[default_state_names.triage]");
  });

  it("keeps the name of a state the user created or renamed", () => {
    expect(getStateName("In review", t)).toBe("In review");
    expect(getStateName("Gotowe", t)).toBe("Gotowe");
    expect(getStateName("done", t)).toBe("done");
    expect(getStateName("", t)).toBe("");
  });
});
