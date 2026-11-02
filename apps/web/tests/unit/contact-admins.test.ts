/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { EUserPermissions } from "@plane/constants";
import type { IWorkspaceMember } from "@plane/types";
import { buildMailtoHref, getContactableAdmins } from "../../helpers/contact-admins";

const member = (
  id: string,
  role: EUserPermissions,
  overrides: Partial<IWorkspaceMember["member"]> = {},
  active = true
): IWorkspaceMember =>
  ({
    id: `membership-${id}`,
    role,
    is_active: active,
    member: { id, display_name: `Name ${id}`, email: `${id}@example.com`, is_bot: false, ...overrides },
  }) as IWorkspaceMember;

describe("getContactableAdmins", () => {
  it("keeps only the admins", () => {
    const admins = getContactableAdmins([
      member("a", EUserPermissions.ADMIN),
      member("m", EUserPermissions.MEMBER),
      member("g", EUserPermissions.GUEST),
    ]);

    expect(admins.map((admin) => admin.id)).toEqual(["a"]);
  });

  it("leaves out the person asking, deactivated admins and bots", () => {
    const admins = getContactableAdmins(
      [
        member("me", EUserPermissions.ADMIN),
        member("gone", EUserPermissions.ADMIN, {}, false),
        member("bot", EUserPermissions.ADMIN, { is_bot: true }),
        member("other", EUserPermissions.ADMIN),
      ],
      "me"
    );

    expect(admins.map((admin) => admin.id)).toEqual(["other"]);
  });

  it("keeps an admin whose email is hidden from this role, without an address", () => {
    const [admin] = getContactableAdmins([member("a", EUserPermissions.ADMIN, { email: undefined })]);

    expect(admin).toEqual({ id: "a", name: "Name a", email: null });
  });

  it("copes with members that are not loaded", () => {
    expect(getContactableAdmins([null, undefined, member("a", EUserPermissions.ADMIN)])).toHaveLength(1);
  });

  it("lists an admin once", () => {
    expect(
      getContactableAdmins([member("a", EUserPermissions.ADMIN), member("a", EUserPermissions.ADMIN)])
    ).toHaveLength(1);
  });
});

describe("buildMailtoHref", () => {
  it("addresses everybody and encodes the subject and the body", () => {
    const href = buildMailtoHref(["a@example.com", "b@example.com"], "Question for Acme & co", "Hello,\n\nAda");

    expect(href).toBe(
      "mailto:a@example.com,b@example.com?subject=Question%20for%20Acme%20%26%20co&body=Hello%2C%0A%0AAda"
    );
  });

  it("leaves out empty and repeated addresses", () => {
    expect(buildMailtoHref(["a@example.com", " ", "a@example.com"], "s", "b")).toBe(
      "mailto:a@example.com?subject=s&body=b"
    );
  });

  it("encodes an address that carries characters of its own", () => {
    expect(buildMailtoHref(["a+b@example.com"], "s", "b")).toContain("mailto:a%2Bb@example.com?");
  });

  it("gives nothing when there is nobody to write to", () => {
    expect(buildMailtoHref([], "s", "b")).toBeNull();
  });
});
