/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TIssueType, TIssueTypeKind, TProjectIssueType } from "@plane/types";
import {
  getAssignableIssueTypes,
  getBulkAssignDefaultTypeId,
  getDefaultProjectIssueTypeId,
  getLockedProjectIssueType,
  getSelectableProjectIssueTypes,
  getSystemManagedTypeNames,
  isSystemManagedTypeName,
} from "../../helpers/issue-type-options";
import {
  buildIssueTypePayloadFromForm,
  canToggleEpicKind,
  getKindBadgeKey,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-types/work-item-type-payload-helpers";
import { DEFAULT_WORK_ITEM_TYPE_FORM } from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-types/work-item-type-form.types";
import { buildProjectTemplatePayloadFromFormValues } from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/project-templates/project-template-payload-helpers";
import type { TProjectTemplateFormFields } from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/project-templates/project-template-form.types";

const type = (id: string, kind?: TIssueTypeKind, extra: Partial<TIssueType> = {}): TIssueType => ({
  id,
  name: id,
  description: "",
  logo_props: { in_use: "icon" },
  is_epic: kind === "epic",
  ...(kind ? { kind } : {}),
  is_default: false,
  is_active: true,
  level: 0,
  properties: [],
  project_ids: [],
  created_at: "",
  updated_at: "",
  ...extra,
});

const link = (issueType: TIssueType | undefined, id: string, isDefault = false): TProjectIssueType => ({
  id: `link-${id}`,
  issue_type_id: id,
  issue_type_detail: issueType,
  level: 0,
  is_default: isDefault,
});

const task = type("task", "standard");
const bug = type("bug", "standard");
const epic = type("epic", "epic");
const milestone = type("milestone", "milestone");
const approval = type("approval", "approval");
const review = type("review", "review");

const allLinks = [approval, task, epic, milestone, review, bug].map((row) => link(row, row.id));
const ids = (rows: { issue_type_id: string }[]) => rows.map((row) => row.issue_type_id);

describe("getSelectableProjectIssueTypes", () => {
  it("leaves out the system-managed kinds and keeps the rest in order", () => {
    expect(ids(getSelectableProjectIssueTypes(allLinks))).toEqual(["task", "epic", "milestone", "bug"]);
  });

  it("offers Epic types like any other type", () => {
    expect(ids(getSelectableProjectIssueTypes([link(epic, "epic")]))).toEqual(["epic"]);
  });

  it("includes the system-managed kinds when the caller asks", () => {
    expect(ids(getSelectableProjectIssueTypes(allLinks, { includeSystemManaged: true }))).toHaveLength(6);
  });

  it("drops links that came without the details of their type", () => {
    expect(getSelectableProjectIssueTypes([link(undefined, "gone")])).toEqual([]);
  });

  it("keeps types cached without a kind, read through is_epic", () => {
    const cached = [link(type("old"), "old"), link(type("old-epic", undefined, { is_epic: true }), "old-epic")];
    expect(ids(getSelectableProjectIssueTypes(cached))).toEqual(["old", "old-epic"]);
  });
});

describe("getDefaultProjectIssueTypeId", () => {
  it("is the default type of the project", () => {
    expect(getDefaultProjectIssueTypeId([link(task, "task"), link(bug, "bug", true)])).toBe("bug");
  });

  it("falls back to the first type a person can pick, never a system-managed one", () => {
    expect(getDefaultProjectIssueTypeId([link(approval, "approval"), link(task, "task")])).toBe("task");
  });

  it("ignores a system-managed type marked as the default", () => {
    expect(getDefaultProjectIssueTypeId([link(approval, "approval", true), link(task, "task")])).toBe("task");
  });

  it("is null when nothing can be picked", () => {
    expect(getDefaultProjectIssueTypeId([link(review, "review")])).toBeNull();
    expect(getDefaultProjectIssueTypeId([])).toBeNull();
  });
});

describe("getLockedProjectIssueType", () => {
  it("returns the link of a system-managed type", () => {
    expect(getLockedProjectIssueType(allLinks, "approval")?.issue_type_id).toBe("approval");
    expect(getLockedProjectIssueType(allLinks, "review")?.issue_type_id).toBe("review");
  });

  it("is null for the kinds a person can switch", () => {
    expect(getLockedProjectIssueType(allLinks, "task")).toBeNull();
    expect(getLockedProjectIssueType(allLinks, "epic")).toBeNull();
    expect(getLockedProjectIssueType(allLinks, "milestone")).toBeNull();
  });

  it("is null without a type and for a type the project does not link", () => {
    expect(getLockedProjectIssueType(allLinks, null)).toBeNull();
    expect(getLockedProjectIssueType(allLinks, undefined)).toBeNull();
    expect(getLockedProjectIssueType(allLinks, "unknown")).toBeNull();
  });
});

describe("getAssignableIssueTypes", () => {
  const workspaceTypes = [task, epic, milestone, approval, review, bug];

  it("never lists the system-managed kinds", () => {
    expect(getAssignableIssueTypes(workspaceTypes).map((row) => row.id)).toEqual(["task", "epic", "milestone", "bug"]);
  });

  it("leaves Epic types out as well where Epics have their own switch", () => {
    expect(getAssignableIssueTypes(workspaceTypes, { hideEpics: true }).map((row) => row.id)).toEqual([
      "task",
      "milestone",
      "bug",
    ]);
  });

  it("hides an Epic type that was cached without a kind", () => {
    const cachedEpic = type("old-epic", undefined, { is_epic: true });
    expect(getAssignableIssueTypes([task, cachedEpic], { hideEpics: true }).map((row) => row.id)).toEqual(["task"]);
  });
});

describe("getBulkAssignDefaultTypeId", () => {
  it("keeps the current default while it stays in the list", () => {
    expect(getBulkAssignDefaultTypeId(["approval", "task", "bug"], allLinks, "bug")).toBe("bug");
  });

  it("moves to the first type that is not system-managed when the default was unticked", () => {
    expect(getBulkAssignDefaultTypeId(["approval", "review", "task", "bug"], allLinks, "milestone")).toBe("task");
  });

  it("is null when only system-managed types are left", () => {
    expect(getBulkAssignDefaultTypeId(["approval", "review"], allLinks, "task")).toBeNull();
    expect(getBulkAssignDefaultTypeId([], allLinks, undefined)).toBeNull();
  });
});

describe("system-managed type names", () => {
  const names = getSystemManagedTypeNames([
    task,
    type("a", "approval", { name: " Akceptacja " }),
    type("r", "review", { name: "Review" }),
  ]);

  it("collects the names of the system-managed types only", () => {
    expect(names).toEqual(["Akceptacja", "Review"]);
  });

  it("matches the exact name, as the server does", () => {
    expect(isSystemManagedTypeName("Review", names)).toBe(true);
    expect(isSystemManagedTypeName("  Akceptacja ", names)).toBe(true);
    expect(isSystemManagedTypeName("review", names)).toBe(false);
    expect(isSystemManagedTypeName("Bug", names)).toBe(false);
    expect(isSystemManagedTypeName("", names)).toBe(false);
  });
});

describe("work item type form", () => {
  const values = { ...DEFAULT_WORK_ITEM_TYPE_FORM, name: " Approval ", isActive: false, projectIds: ["p1"] };

  it("offers the Epic switch for the standard and Epic kinds only", () => {
    expect(canToggleEpicKind("standard")).toBe(true);
    expect(canToggleEpicKind("epic")).toBe(true);
    expect(canToggleEpicKind("milestone")).toBe(false);
    expect(canToggleEpicKind("approval")).toBe(false);
    expect(canToggleEpicKind("review")).toBe(false);
  });

  it("names every kind but the standard one", () => {
    expect(getKindBadgeKey("standard")).toBeNull();
    expect(getKindBadgeKey("epic")).toBe("workspace_settings.settings.work_item_types.epic_badge");
    expect(getKindBadgeKey("approval")).toBe("workspace_settings.settings.work_item_types.kinds.approval");
  });

  it("sends every field for a standard type", () => {
    expect(buildIssueTypePayloadFromForm(values)).toMatchObject({
      name: "Approval",
      is_epic: false,
      is_active: false,
      project_ids: ["p1"],
    });
  });

  it("sends neither the active flag, the projects nor the Epic flag for a system-managed type", () => {
    const payload = buildIssueTypePayloadFromForm(values, "approval");
    expect(payload).toMatchObject({ name: "Approval", properties: [] });
    expect(payload).not.toHaveProperty("is_active");
    expect(payload).not.toHaveProperty("project_ids");
    expect(payload).not.toHaveProperty("is_epic");
  });

  it("keeps the active flag and the projects of a milestone type, without the Epic flag", () => {
    const payload = buildIssueTypePayloadFromForm(values, "milestone");
    expect(payload).toMatchObject({ is_active: false, project_ids: ["p1"] });
    expect(payload).not.toHaveProperty("is_epic");
  });
});

describe("project template: additional work item types", () => {
  const formValues = {
    projectName: "",
    projectIdentifier: "",
    projectDescription: "",
    coverImageUrl: "",
    features: { is_issue_type_enabled: true },
    taskCustomProperties: [],
    epicEnabled: false,
    epicCustomProperties: [],
    additionalWorkItemTypes: [
      { id: "1", name: "Bug", description: "", customProperties: [] },
      { id: "2", name: "Approval", description: "", customProperties: [] },
    ],
    stateTemplates: [],
    labelTemplates: [],
    groups: [],
  } as unknown as TProjectTemplateFormFields;

  it("leaves out an entry named like a system-managed type", () => {
    const payload = buildProjectTemplatePayloadFromFormValues(formValues, new Map(), ["Approval"]);
    expect(payload.additional_work_item_types?.map((row) => row.name)).toEqual(["Bug"]);
  });

  it("keeps every entry when the workspace has no such type", () => {
    const payload = buildProjectTemplatePayloadFromFormValues(formValues);
    expect(payload.additional_work_item_types?.map((row) => row.name)).toEqual(["Bug", "Approval"]);
  });
});
