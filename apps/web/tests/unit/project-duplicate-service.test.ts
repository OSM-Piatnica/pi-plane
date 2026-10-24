/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectService } from "@/services/project/project.service";

const post = vi.hoisted(() => vi.fn());

vi.mock("@/services/api.service", () => ({
  APIService: class {
    post = post;
  },
}));

describe("ProjectService.duplicateProject", () => {
  beforeEach(() => {
    post.mockReset();
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
