/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectService } from "@/services/project/project.service";

const post = vi.hoisted(() => vi.fn());
const get = vi.hoisted(() => vi.fn());

vi.mock("@/services/api.service", () => ({
  APIService: class {
    post = post;
    get = get;
  },
}));

describe("ProjectService.duplicateProject", () => {
  beforeEach(() => {
    post.mockReset();
    get.mockReset();
  });

  it("names the source project in the path, never the body", async () => {
    post.mockResolvedValue({ data: { id: "copy" } });
    const payload = { name: "Acme (Copy)", include: { labels: true } };

    const copy = await new ProjectService().duplicateProject("acme", "source-id", payload);

    // The API scopes its project-level permission check to this path segment.
    expect(post).toHaveBeenCalledWith("/api/workspaces/acme/projects/source-id/duplicate/", payload);
    expect(copy).toEqual({ id: "copy" });
  });

  it("rejects with the response so callers can read the API's error codes", async () => {
    const response = { status: 400, data: { error: "PROJECT_NAME_ALREADY_EXIST" } };
    post.mockRejectedValue({ response });

    await expect(new ProjectService().duplicateProject("acme", "source-id", {})).rejects.toBe(response);
  });
});

describe("ProjectService project copy status", () => {
  beforeEach(() => {
    post.mockReset();
    get.mockReset();
  });

  it("reads the job through the copied project", async () => {
    get.mockResolvedValue({ data: { job: { id: "job", status: "processing", copied: 3, total: 10 } } });

    const job = await new ProjectService().getProjectCopyStatus("acme", "copy-id");

    expect(get).toHaveBeenCalledWith("/api/workspaces/acme/projects/copy-id/copy-status/");
    expect(job).toMatchObject({ status: "processing", copied: 3 });
  });

  it("reports no job for a project that was never copied", async () => {
    get.mockResolvedValue({ data: { job: null } });

    expect(await new ProjectService().getProjectCopyStatus("acme", "copy-id")).toBeNull();
  });

  it("asks a failed copy to carry on", async () => {
    post.mockResolvedValue({ data: { job: { id: "job", status: "queued" } } });

    const job = await new ProjectService().retryProjectCopy("acme", "copy-id");

    expect(post).toHaveBeenCalledWith("/api/workspaces/acme/projects/copy-id/copy-retry/");
    expect(job).toMatchObject({ status: "queued" });
  });

  it("rejects with the response so callers can read the API's error codes", async () => {
    const response = { status: 409, data: { error: "PROJECT_COPY_NOT_RETRYABLE" } };
    post.mockRejectedValue({ response });

    await expect(new ProjectService().retryProjectCopy("acme", "copy-id")).rejects.toBe(response);
  });
});
