/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { RACI_FILTER_MY_DEPARTMENT } from "@plane/constants";
import { RACI_ROLES } from "@plane/types";
import type { TIssueRaciEntry } from "@plane/types";
import {
  canEditRaci,
  getRaciBarBackground,
  getRaciChipLabel,
  getRaciChipTextColor,
  getRaciDepartments,
  getRaciEditorDepartments,
  getRaciFilterOptions,
  getRaciFilterRole,
  getRaciLetterKey,
  getRaciRole,
  isSameRaci,
  sanitizeRaci,
  setRaciRole,
} from "@plane/utils";

const LOCALES = path.resolve(import.meta.dirname, "../../../../packages/i18n/src/locales");
const raciOf = (locale: string) =>
  JSON.parse(readFileSync(path.join(LOCALES, locale, "pi-extensions.json"), "utf8")).raci as {
    roles: Record<string, { letter: string; name: string }>;
  };
const lettersOf = (locale: string) => RACI_ROLES.map((role) => raciOf(locale).roles[role].letter).join("");

const department = (id: string, name: string, sort_order: number, extra: Record<string, unknown> = {}) => ({
  id,
  name,
  code: id.toUpperCase(),
  color: "",
  sort_order,
  is_external: false,
  is_active: true,
  ...extra,
});

describe("RACI letters per locale", () => {
  it("are O / Z / K / I in Polish and R / A / C / I in English", () => {
    expect(lettersOf("pl")).toBe("OZKI");
    expect(lettersOf("pl-x-podlaski")).toBe("OZKI");
    expect(lettersOf("en")).toBe("RACI");
  });

  it("exist for every role in every locale, one letter each, with a full name", () => {
    for (const locale of readdirSync(LOCALES)) {
      const raci = raciOf(locale);
      for (const role of RACI_ROLES) {
        expect(raci.roles[role].letter, `${locale} ${role}`).toMatch(/^\p{Lu}$/u);
        expect(raci.roles[role].name.length, `${locale} ${role}`).toBeGreaterThan(1);
      }
      // the letters of one locale tell the roles apart
      expect(new Set(lettersOf(locale)).size).toBe(4);
    }
  });

  it("are read through translation keys, never from code", () => {
    expect(getRaciLetterKey("approver")).toBe("raci.roles.approver.letter");
  });
});

describe("RACI entries", () => {
  const entries: TIssueRaciEntry[] = [
    { group_id: "rm", role: "responsible" },
    { group_id: "qa", role: "approver" },
  ];

  it("gives a department one role, replacing the one it had", () => {
    expect(getRaciRole(entries, "qa")).toBe("approver");
    expect(getRaciRole(entries, "pr")).toBeNull();
    expect(setRaciRole(entries, "qa", "informed")).toEqual([
      { group_id: "rm", role: "responsible" },
      { group_id: "qa", role: "informed" },
    ]);
    expect(setRaciRole(entries, "rm", null)).toEqual([{ group_id: "qa", role: "approver" }]);
    expect(setRaciRole(undefined, "rm", "consulted")).toEqual([{ group_id: "rm", role: "consulted" }]);
  });

  it("allows several responsible departments", () => {
    const both = setRaciRole(entries, "qa", "responsible");
    expect(both.filter((entry) => entry.role === "responsible")).toHaveLength(2);
  });

  it("keeps known roles only and the last role of a department when building a payload", () => {
    const messy = [
      { group_id: "rm", role: "responsible" },
      { group_id: "rm", role: "consulted" },
      { group_id: "qa", role: "owner" },
    ] as unknown as TIssueRaciEntry[];
    expect(sanitizeRaci(messy)).toEqual([{ group_id: "rm", role: "consulted" }]);
  });

  it("compares lists regardless of order", () => {
    expect(isSameRaci(entries, entries.toReversed())).toBe(true);
    expect(isSameRaci(entries, [entries[0]])).toBe(false);
    expect(isSameRaci(entries, setRaciRole(entries, "qa", "informed"))).toBe(false);
  });
});

describe("RACI departments", () => {
  const rm = department("rm", "Marketing", 2, { color: "#3f76ff" });
  const qa = department("qa", "Quality", 1, { color: "#ffffff" });
  const old = department("old", "Closed", 3, { is_active: false });
  const byId = new Map([rm, qa, old].map((item) => [item.id, item]));

  it("lists the departments with a role in the order of departments, leaving out unknown ones", () => {
    const entries: TIssueRaciEntry[] = [
      { group_id: "rm", role: "responsible" },
      { group_id: "gone", role: "responsible" },
      { group_id: "qa", role: "responsible" },
      { group_id: "old", role: "approver" },
    ];
    expect(getRaciDepartments(entries, "responsible", byId).map((item) => item.id)).toEqual(["qa", "rm"]);
    expect(getRaciDepartments(entries, "approver", byId).map((item) => item.id)).toEqual(["old"]);
  });

  it("offers switched-off departments in the editor only while they have a role", () => {
    expect(getRaciEditorDepartments([rm, qa, old], []).map((item) => item.id)).toEqual(["qa", "rm"]);
    expect(
      getRaciEditorDepartments([rm, qa, old], [{ group_id: "old", role: "informed" }]).map((item) => item.id)
    ).toEqual(["qa", "rm", "old"]);
  });

  it("labels chips by code, else by name, with readable text on the department colour", () => {
    expect(getRaciChipLabel(rm)).toBe("RM");
    expect(getRaciChipLabel({ name: "Logistics", code: "" })).toBe("Logistics");
    expect(getRaciChipTextColor("#ffffff")).toBe("#1f2937");
    expect(getRaciChipTextColor("#000")).toBe("#ffffff");
    expect(getRaciChipTextColor("")).toBeUndefined();
    expect(getRaciChipTextColor("red")).toBeUndefined();
  });

  it("colours a timeline bar by one department, or in stripes for several", () => {
    expect(getRaciBarBackground([])).toBeUndefined();
    expect(getRaciBarBackground(["", null])).toBeUndefined();
    expect(getRaciBarBackground(["#3f76ff"])).toBe("#3f76ff");
    expect(getRaciBarBackground(["#3f76ff", "", "#ef4444"])).toBe(
      "linear-gradient(90deg, #3f76ff 0% 50%, #ef4444 50% 100%)"
    );
  });
});

describe("RACI edit rights", () => {
  it("are for project admins and the project lead", () => {
    expect(canEditRaci({ isProjectAdmin: true, projectLead: null, userId: "u1" })).toBe(true);
    expect(canEditRaci({ isProjectAdmin: false, projectLead: "u1", userId: "u1" })).toBe(true);
    expect(canEditRaci({ isProjectAdmin: false, projectLead: { id: "u1" }, userId: "u1" })).toBe(true);
    expect(canEditRaci({ isProjectAdmin: false, projectLead: "u2", userId: "u1" })).toBe(false);
    expect(canEditRaci({ isProjectAdmin: false, projectLead: undefined, userId: undefined })).toBe(false);
  });
});

describe("RACI filters", () => {
  it("map filter keys to roles", () => {
    expect(getRaciFilterRole("raci_department_id")).toBeNull();
    expect(getRaciFilterRole("raci_responsible_id")).toBe("responsible");
    expect(getRaciFilterRole("raci_informed_id")).toBe("informed");
    expect(getRaciFilterRole("raci_owner_id")).toBeUndefined();
    expect(getRaciFilterRole("assignee_id")).toBeUndefined();
  });

  it("offer My department first, then the departments in their order", () => {
    const options = getRaciFilterOptions([
      department("rm", "Marketing", 2),
      department("qa", "Quality", 1, { code: "" }),
    ]);
    expect(options.map((option) => option.value)).toEqual([RACI_FILTER_MY_DEPARTMENT, "qa", "rm"]);
    expect(options.map((option) => option.label)).toEqual(["My department", "Quality", "RM · Marketing"]);
    expect(getRaciFilterOptions([], (key) => `t:${key}`)[0].label).toBe("t:raci.my_department");
  });
});
