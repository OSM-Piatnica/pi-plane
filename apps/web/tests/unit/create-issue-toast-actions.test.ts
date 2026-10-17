/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { setToast, copyTextToClipboard, copyUrlToClipboard } = vi.hoisted(() => ({
  setToast: vi.fn(),
  copyTextToClipboard: vi.fn(),
  copyUrlToClipboard: vi.fn(),
}));

vi.mock("@plane/blocks/toast", () => ({ setToast }));
vi.mock("@plane/utils", () => ({ copyTextToClipboard, copyUrlToClipboard, generateWorkItemLink: vi.fn() }));
vi.mock("@plane/i18n", () => ({ useTranslation: vi.fn() }));
vi.mock("@/hooks/store/use-issue-detail", () => ({ useIssueDetail: vi.fn() }));
vi.mock("@/hooks/store/use-project", () => ({ useProject: vi.fn() }));

import { buildWorkItemToastActions } from "../../components/issues/create-issue-toast-action-items";

const t = (key: string) => key;
const build = (isEpic = false) =>
  buildWorkItemToastActions({ t, workItemLink: "/acme/browse/PROJ-1/", identifier: "PROJ-1", isEpic });

/** Lets the promise chain behind a click settle. */
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("buildWorkItemToastActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    copyUrlToClipboard.mockResolvedValue(undefined);
    copyTextToClipboard.mockResolvedValue(undefined);
  });

  it("offers copy link, the identifier and a primary view action", () => {
    const [copyLink, copyId, view] = build();
    expect(copyLink?.label).toBe("common.actions.copy_link");
    expect(copyId?.label).toBe("PROJ-1");
    expect(view).toMatchObject({ label: "issue_ui.view_work_item", href: "/acme/browse/PROJ-1/", primary: true });
  });

  it("labels the view action for epics", () => {
    expect(build(true)[2]?.label).toBe("issue_ui.view_epic");
  });

  it("confirms a link copy with a success toast", async () => {
    build()[0]?.onClick?.();
    await flush();
    expect(copyUrlToClipboard).toHaveBeenCalledWith("/acme/browse/PROJ-1/");
    expect(setToast).toHaveBeenCalledWith({ type: "success", title: "common.link_copied" });
  });

  it("confirms an identifier copy with a Copied! toast", async () => {
    build()[1]?.onClick?.();
    await flush();
    expect(copyTextToClipboard).toHaveBeenCalledWith("PROJ-1");
    expect(setToast).toHaveBeenCalledWith({ type: "success", title: "common.copied" });
  });

  it("reports an error toast when the clipboard is unavailable", async () => {
    copyUrlToClipboard.mockRejectedValue(new Error("denied"));
    build()[0]?.onClick?.();
    await flush();
    expect(setToast).toHaveBeenCalledTimes(1);
    expect(setToast).toHaveBeenCalledWith(expect.objectContaining({ type: "error" }));
  });
});
