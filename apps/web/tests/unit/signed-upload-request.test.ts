/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { buildSignedUploadRequest } from "@plane/services";
import type { TFileSignedURLResponse } from "@plane/types";

const file = new File(["hello"], "hello.png", { type: "image/png" });

const response = (upload_data: TFileSignedURLResponse["upload_data"]): TFileSignedURLResponse => ({
  asset_id: "asset",
  asset_url: "/asset",
  upload_data,
});

describe("the request that uploads a file to the signed upload", () => {
  it("posts a multipart form to an S3-compatible store", () => {
    const request = buildSignedUploadRequest(
      response({ url: "https://bucket.example/", fields: { key: "k", policy: "p", "Content-Type": "image/png" } }),
      file
    );
    expect(request.method).toBe("post");
    expect(request.url).toBe("https://bucket.example/");
    expect(request.headers).toEqual({ "Content-Type": "multipart/form-data" });
    const form = request.data as FormData;
    expect(form.get("key")).toBe("k");
    expect(form.get("policy")).toBe("p");
    expect(form.get("file")).toBeInstanceOf(File);
  });

  it("puts the file itself to Azure Blob Storage, with the headers it asks for", () => {
    const headers = {
      "x-ms-blob-type": "BlockBlob",
      "x-ms-blob-content-type": "image/png",
      "Content-Type": "image/png",
    };
    const request = buildSignedUploadRequest(
      response({ url: "https://acct.blob.core.windows.net/c/k?sig=1", fields: {}, method: "PUT", headers }),
      file
    );
    expect(request.method).toBe("put");
    expect(request.url).toBe("https://acct.blob.core.windows.net/c/k?sig=1");
    expect(request.data).toBe(file);
    expect(request.headers).toEqual(headers);
  });

  it("does not hand the response's own headers object to the request", () => {
    const headers = { "x-ms-blob-type": "BlockBlob" };
    const request = buildSignedUploadRequest(response({ url: "u", fields: {}, method: "PUT", headers }), file);
    expect(request.headers).not.toBe(headers);
  });

  it("is a form post when the storage did not say how", () => {
    expect(buildSignedUploadRequest(response({ url: "u", fields: {} }), file).method).toBe("post");
  });
});
