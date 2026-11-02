/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// helpers
import { getContactableAdmins } from "@/helpers/contact-admins";
import type { TContactableAdmin } from "@/helpers/contact-admins";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";

/** The admins of the current workspace the signed-in person can write to (everybody but themselves). */
export const useContactableAdmins = (): {
  admins: TContactableAdmin[];
  fetchMembers: (slug: string) => Promise<unknown>;
} => {
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails, fetchWorkspaceMembers },
  } = useMember();
  const { data: currentUser } = useUser();

  const members = (workspaceMemberIds ?? []).map((id) => getWorkspaceMemberDetails(id));
  const admins = getContactableAdmins(members, currentUser?.id);

  return { admins, fetchMembers: fetchWorkspaceMembers };
};
