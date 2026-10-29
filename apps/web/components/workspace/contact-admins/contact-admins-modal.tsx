/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
// helpers
import { buildMailtoHref } from "@/helpers/contact-admins";
// hooks
import { useContactableAdmins } from "./use-contactable-admins";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

/** Who the admins of this workspace are, and one button that opens an email to all of them. */
export const ContactWorkspaceAdminsModal = observer(function ContactWorkspaceAdminsModal(props: Props) {
  const { isOpen, onClose } = props;
  // router
  const { workspaceSlug } = useParams();
  // translation
  const { t } = useTranslation();
  // store hooks
  const { currentWorkspace } = useWorkspace();
  const { data: currentUser } = useUser();
  const { admins, fetchMembers } = useContactableAdmins();

  // the list is shown from what the app already loaded; this only makes sure it is there and up to date
  useSWR(isOpen && workspaceSlug ? `CONTACT_ADMINS_MEMBERS_${workspaceSlug}` : null, () =>
    fetchMembers(workspaceSlug.toString())
  );

  const workspaceName = currentWorkspace?.name ?? "";
  const mailtoHref = buildMailtoHref(
    admins.flatMap((admin) => (admin.email ? [admin.email] : [])),
    t("contact_workspace_admins.subject", { workspace: workspaceName }),
    t("contact_workspace_admins.body", {
      name: currentUser?.display_name || [currentUser?.first_name, currentUser?.last_name].join(" ").trim(),
    })
  );
  const emailAllLabel = t("contact_workspace_admins.email_all");

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="lg">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("contact_workspace_admins.title")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-4">
              <p className="text-13 leading-6 text-secondary">
                {t("contact_workspace_admins.description", { workspace: workspaceName })}
              </p>
              <ul className="flex max-h-72 flex-col divide-y divide-subtle overflow-y-auto rounded-lg border border-subtle">
                {admins.map((admin) => (
                  <li key={admin.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <span className="truncate text-13 font-medium text-primary">{admin.name}</span>
                    {admin.email && <span className="truncate text-13 text-secondary">{admin.email}</span>}
                  </li>
                ))}
              </ul>
              {mailtoHref ? (
                <div className="flex justify-end">
                  <Button
                    variant="primary"
                    size="md"
                    stretch="auto"
                    nativeButton={false}
                    render={<a href={mailtoHref}>{emailAllLabel}</a>}
                    label={emailAllLabel}
                  />
                </div>
              ) : (
                <p className="rounded-md bg-layer-1 p-3 text-13 text-secondary">
                  {t("contact_workspace_admins.no_email_addresses")}
                </p>
              )}
            </div>
          </DialogBody>
        </DialogMain>
      </DialogContent>
    </Dialog>
  );
});
