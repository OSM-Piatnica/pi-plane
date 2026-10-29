/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

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
import type { TNotification } from "@plane/types";
// helpers
import { buildMailtoHref } from "@/helpers/contact-admins";

type Props = {
  notification: TNotification;
  isOpen: boolean;
  onClose: () => void;
};

/** The whole of a message to the admins (the inbox shows its beginning) and a way to answer it by email. */
export function AdminMessageModal(props: Props) {
  const { notification, isOpen, onClose } = props;
  const { t } = useTranslation();
  const message = notification.data?.workspace_admin_message;
  const sender = notification.triggered_by_details;
  const senderName = sender?.display_name || sender?.first_name || message?.sender_email || "";
  const replyHref = message?.sender_email ? buildMailtoHref([message.sender_email], "", "") : null;
  const replyLabel = t("contact_workspace_admins.reply_by_email");

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
              <DialogTitle>{t("contact_workspace_admins.message_from", { name: senderName })}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-3">
              {message?.sender_email && <p className="text-13 text-secondary">{message.sender_email}</p>}
              <p className="max-h-80 overflow-y-auto text-14 leading-6 break-words whitespace-pre-wrap text-primary">
                {message?.message}
              </p>
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" label={t("close")} onClick={onClose} />
          {replyHref && (
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              nativeButton={false}
              render={<a href={replyHref}>{replyLabel}</a>}
              label={replyLabel}
            />
          )}
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
