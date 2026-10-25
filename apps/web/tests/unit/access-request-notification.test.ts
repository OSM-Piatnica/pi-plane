/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  getAccessRequestNotificationPath,
  getAccessRequestNotificationTextKey,
} from "@/helpers/access-request-notification";

describe("access request notifications", () => {
  it("says what happened to the request", () => {
    expect(getAccessRequestNotificationTextKey(undefined)).toBe("notification.access_request.requested");
    expect(getAccessRequestNotificationTextKey("approved")).toBe("notification.access_request.approved");
    expect(getAccessRequestNotificationTextKey("rejected")).toBe("notification.access_request.rejected");
  });

  it("leads the admins to the members settings, an approved requester into the project, a rejected one to the list", () => {
    expect(getAccessRequestNotificationPath(undefined, "acme", "p1")).toBe("/acme/settings/projects/p1/members/");
    expect(getAccessRequestNotificationPath("approved", "acme", "p1")).toBe("/acme/projects/p1/issues/");
    expect(getAccessRequestNotificationPath("rejected", "acme", "p1")).toBe("/acme/projects/");
  });
});
