/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { TextArea, TextAreaGroup } from "@makeplane/propel/components/text-area";
import { setToast } from "@plane/blocks/toast";
// helpers
import { buildMailtoHref } from "@/helpers/contact-admins";
import { ADMIN_MESSAGE_MAX_LENGTH, getAdminMessageFailure } from "@/helpers/contact-admins-errors";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUser } from "@/hooks/store/user";
// services
import { workspaceAdminMessageService } from "@/services/workspace-admin-message.service";
// local imports
import { useContactableAdmins } from "./use-contactable-admins";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

/**
 * Who the admins of this workspace are, a message to them (it reaches their inbox and their email) and, for people
 * who would rather write from their own mail app, one button that opens an email to all of them.
 */
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
  // states
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  // the list is shown from what the app already loaded; this only makes sure it is there and up to date
  useSWR(isOpen && workspaceSlug ? `CONTACT_ADMINS_MEMBERS_${workspaceSlug}` : null, () =>
    fetchMembers(workspaceSlug.toString())
  );

  const workspaceName = currentWorkspace?.name ?? "";
  const senderName = currentUser?.display_name || [currentUser?.first_name, currentUser?.last_name].join(" ").trim();
  const mailtoHref = buildMailtoHref(
    admins.flatMap((admin) => (admin.email ? [admin.email] : [])),
    t("contact_workspace_admins.subject", { workspace: workspaceName }),
    t("contact_workspace_admins.body", { name: senderName })
  );
  const emailAllLabel = t("contact_workspace_admins.email_all");
  const trimmedMessage = message.trim();

  const close = () => {
    if (isSending) return;
    setMessage("");
    onClose();
  };

  const handleSend = async () => {
    if (!workspaceSlug || !trimmedMessage || isSending) return;
    setIsSending(true);
    try {
      await workspaceAdminMessageService.send(workspaceSlug.toString(), trimmedMessage);
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t("contact_workspace_admins.sent"),
      });
      setMessage("");
      onClose();
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message:
          getAdminMessageFailure(error) === "rate_limited"
            ? t("contact_workspace_admins.error_rate_limited")
            : t("contact_workspace_admins.error_generic"),
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) close();
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
              <ul className="flex max-h-48 flex-col divide-y divide-subtle overflow-y-auto rounded-lg border border-subtle">
                {admins.map((admin) => (
                  <li key={admin.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <span className="truncate text-13 font-medium text-primary">{admin.name}</span>
                    {admin.email && <span className="truncate text-13 text-secondary">{admin.email}</span>}
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-1">
                <TextAreaGroup resize="vertical">
                  <TextArea
                    size="md"
                    surface="field"
                    rows={4}
                    maxLength={ADMIN_MESSAGE_MAX_LENGTH}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder={t("contact_workspace_admins.message_placeholder")}
                    aria-label={t("contact_workspace_admins.message_label")}
                  />
                </TextAreaGroup>
                <span className="self-end text-11 text-tertiary">
                  {t("contact_workspace_admins.characters", { count: message.length, max: ADMIN_MESSAGE_MAX_LENGTH })}
                </span>
              </div>
              {mailtoHref && (
                <div className="flex flex-wrap items-center justify-between gap-2 text-13 text-secondary">
                  <span>{t("contact_workspace_admins.or_email")}</span>
                  <Button
                    variant="secondary"
                    size="md"
                    stretch="auto"
                    nativeButton={false}
                    render={<a href={mailtoHref}>{emailAllLabel}</a>}
                    label={emailAllLabel}
                  />
                </div>
              )}
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={close} />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            label={t("contact_workspace_admins.send")}
            onClick={handleSend}
            loading={isSending}
            disabled={!trimmedMessage}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});
