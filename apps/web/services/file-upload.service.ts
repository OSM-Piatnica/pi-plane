/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { AxiosRequestConfig } from "axios";
import axios from "axios";
// plane imports
import { buildSignedUploadRequest } from "@plane/services";
import type { TFileSignedURLResponse } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class FileUploadService extends APIService {
  private cancelSource: any;

  constructor() {
    super("");
  }

  async uploadFile(
    url: string,
    data: FormData,
    uploadProgressHandler?: AxiosRequestConfig["onUploadProgress"]
  ): Promise<void> {
    // oxlint-disable-next-line import/no-named-as-default-member -- axios types declare CancelToken as a type-only export
    this.cancelSource = axios.CancelToken.source();
    return this.post(url, data, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      cancelToken: this.cancelSource.token,
      withCredentials: false,
      onUploadProgress: uploadProgressHandler,
    })
      .then((response) => response?.data)
      .catch((error) => {
        // oxlint-disable-next-line import/no-named-as-default-member -- axios types declare isCancel on the default export only
        if (axios.isCancel(error)) {
          console.log(error.message);
        } else {
          throw error?.response?.data;
        }
      });
  }

  /**
   * Uploads a file the way the storage asked for in its signed upload: a form post to an S3-compatible store, a PUT
   * of the file to Azure Blob Storage.
   */
  async uploadSignedFile(
    signedURLResponse: TFileSignedURLResponse,
    file: File,
    uploadProgressHandler?: AxiosRequestConfig["onUploadProgress"]
  ): Promise<void> {
    const { method, url, data, headers } = buildSignedUploadRequest(signedURLResponse, file);
    // oxlint-disable-next-line import/no-named-as-default-member -- axios types declare CancelToken as a type-only export
    this.cancelSource = axios.CancelToken.source();
    return this[method](url, data, {
      headers,
      cancelToken: this.cancelSource.token,
      withCredentials: false,
      onUploadProgress: uploadProgressHandler,
    })
      .then((response) => response?.data)
      .catch((error) => {
        // oxlint-disable-next-line import/no-named-as-default-member -- axios types declare isCancel on the default export only
        if (axios.isCancel(error)) {
          console.log(error.message);
        } else {
          throw error?.response?.data;
        }
      });
  }

  cancelUpload() {
    this.cancelSource.cancel("Upload canceled");
  }
}
