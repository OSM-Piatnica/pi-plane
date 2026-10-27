/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// types
import type { IEmailCheckData, IEmailCheckResponse } from "@plane/types";
// services
import { APIService } from "../api.service";

/**
 * Service class for handling authentication-related operations for Plane space application
 * Provides methods for user authentication, password management, and session handling
 * @extends {APIService}
 * @remarks This service is only available for plane sites
 */
export class SitesAuthService extends APIService {
  /**
   * Creates an instance of SitesAuthService
   * Initializes with the base API URL
   */
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  /**
   * Checks if an email exists in the system
   * @param {IEmailCheckData} data - Email data to verify
   * @returns {Promise<IEmailCheckResponse>} Response indicating email status
   * @throws {Error} Throws response data if the request fails
   */
  async emailCheck(data: IEmailCheckData): Promise<IEmailCheckResponse> {
    return this.post("/auth/spaces/email-check/", data, { headers: {} })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Generates a one-time code for email sign-in
   * @param {{ email: string }} data - Object containing the email address
   * @returns {Promise<any>} Response containing the generated one-time code
   * @throws {Error} Throws response data if the request fails
   */
  async generateOneTimeCode(data: { email: string }): Promise<any> {
    return this.post("/auth/spaces/magic-generate/", data, { headers: {} })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
