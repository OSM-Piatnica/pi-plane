/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TProjectGroup, TUserGroup } from "@plane/types";
import { EProjectGroupRole } from "@plane/types";
import {
  getAddableGroups,
  getMemberGroupBadge,
  isMemberOnlyViaGroup,
  isProjectGroupRole,
} from "@/helpers/project-group";

const group = (id: string, name: string) => ({ id, name }) as TUserGroup;
const link = (groupId: string) => ({ id: `l-${groupId}`, group: groupId }) as TProjectGroup;

describe("getMemberGroupBadge", () => {
  it("is via_group for people who are in only through a group", () => {
    expect(getMemberGroupBadge({ via_group: true, group_role: 15, original_role: 15 })).toBe("via_group");
  });
  it("is raised when a group holds the direct member's role at the group role", () => {
    expect(getMemberGroupBadge({ via_group: false, group_role: 15, original_role: 15 })).toBe("raised");
  });
  it("is empty when the person's role is above what the group gives", () => {
    expect(getMemberGroupBadge({ via_group: false, group_role: 15, original_role: 20 })).toBeNull();
  });
  it("is empty without a group role", () => {
    expect(getMemberGroupBadge({ via_group: false, group_role: null, original_role: 15 })).toBeNull();
    expect(getMemberGroupBadge({ original_role: 15 })).toBeNull();
  });
});

describe("isMemberOnlyViaGroup", () => {
  it("reads via_group", () => {
    expect(isMemberOnlyViaGroup({ via_group: true })).toBe(true);
    expect(isMemberOnlyViaGroup({ via_group: false })).toBe(false);
    expect(isMemberOnlyViaGroup({})).toBe(false);
  });
});

describe("getAddableGroups", () => {
  it("leaves out linked groups and sorts by name", () => {
    const result = getAddableGroups([group("a", "Zeta"), group("b", "Alpha"), group("c", "Mid")], [link("c")]);
    expect(result.map((g) => g.id)).toEqual(["b", "a"]);
  });
});

describe("isProjectGroupRole", () => {
  it("accepts Member and Guest only", () => {
    expect(isProjectGroupRole(EProjectGroupRole.MEMBER)).toBe(true);
    expect(isProjectGroupRole(EProjectGroupRole.GUEST)).toBe(true);
    expect(isProjectGroupRole(20)).toBe(false);
  });
});
