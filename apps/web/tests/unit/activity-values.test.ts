/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { getPriorityLabel } from "@/helpers/activity-values";
import { renderAdditionalValue } from "@/components/workspace-notifications/notification-card/content";

// stands in for the translator: shows which key a value is looked up under
const t = (key: string) => `[${key}]`;

describe("getPriorityLabel", () => {
  it("looks up the priorities by their key", () => {
    expect(["urgent", "high", "medium", "low", "none"].map((priority) => getPriorityLabel(priority, t))).toEqual([
      "[activity_feed.profile.priority.urgent]",
      "[activity_feed.profile.priority.high]",
      "[activity_feed.profile.priority.medium]",
      "[activity_feed.profile.priority.low]",
      "[activity_feed.profile.priority.none]",
    ]);
  });

  it("reads an empty priority as none and shows an unknown one as it is stored", () => {
    expect(getPriorityLabel("", t)).toBe("[activity_feed.profile.priority.none]");
    expect(getPriorityLabel(undefined, t)).toBe("[activity_feed.profile.priority.none]");
    expect(getPriorityLabel("critical", t)).toBe("Critical");
  });
});

describe("renderAdditionalValue", () => {
  it("translates a priority and the name of a default state", () => {
    expect(renderAdditionalValue("priority", "high", undefined, t)).toBe("[activity_feed.profile.priority.high]");
    expect(renderAdditionalValue("state", "In Progress", undefined, t)).toBe("[default_state_names.in_progress]");
  });

  it("keeps the name of a state the user made, and the value of any other field", () => {
    expect(renderAdditionalValue("state", "Blocked by legal", undefined, t)).toBe("Blocked by legal");
    expect(renderAdditionalValue("name", "New title", undefined, t)).toBe("New title");
  });
});
