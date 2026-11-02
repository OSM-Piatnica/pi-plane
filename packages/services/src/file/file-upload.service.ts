/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import axios from "axios";
// plane imports
import type { TFileSignedURLResponse } from "@plane/types";
// api service
import { APIService } from "../api.service";
import { buildSignedUploadRequest } from "./helper";

/**
 * Service class for handling file upload operations
 * Handles file uploads
 * @extends {APIService}
 */
export class FileUploadService extends APIService {
  private cancelSource: any;

  constructor() {
    super("");
  }

  /**
   * Uploads a file to the specified signed URL
   * @param {string} url - The URL to upload the file to
   * @param {FormData} data - The form data to upload
   * @returns {Promise<void>} Promise resolving to void
   * @throws {Error} If the request fails
   */
  async uploadFile(url: string, data: FormData): Promise<void> {
    this.cancelSource = axios.CancelToken.source();
    return this.post(url, data, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      cancelToken: this.cancelSource.token,
      withCredentials: false,
    })
      .then((response) => response?.data)
      .catch((error) => {
        if (axios.isCancel(error)) {
          console.log(error.message);
        } else {
          throw error?.response?.data;
        }
      });
  }

  /**
   * Uploads a file the way the storage asked for in its signed upload: a form post to an S3-compatible store, a PUT
   * of the file to Azure Blob Storage
   * @param {TFileSignedURLResponse} signedURLResponse - The signed upload the API answered with
   * @param {File} file - The file to upload
   * @returns {Promise<void>} Promise resolving to void
   * @throws {Error} If the request fails
   */
  async uploadSignedFile(signedURLResponse: TFileSignedURLResponse, file: File): Promise<void> {
    const { method, url, data, headers } = buildSignedUploadRequest(signedURLResponse, file);
    // oxlint-disable-next-line import/no-named-as-default-member -- axios types declare CancelToken as a type-only export
    this.cancelSource = axios.CancelToken.source();
    return this[method](url, data, { headers, cancelToken: this.cancelSource.token, withCredentials: false })
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
   * Cancels the upload
   */
  cancelUpload() {
    this.cancelSource.cancel("Upload canceled");
  }
}
