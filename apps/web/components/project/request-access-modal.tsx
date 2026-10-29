/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
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
import { useTranslation } from "@plane/i18n";
// hooks
import { useProject } from "@/hooks/store/use-project";

type Props = {
  isOpen: boolean;
  workspaceSlug: string;
  projectId: string;
  /** The project's name, when it is known (a direct link may be opened before the gallery is loaded). */
  projectName?: string;
  handleClose: () => void;
  /** Called after the request was sent. */
  onRequested?: () => void;
};

const MESSAGE_MAX_LENGTH = 500;

/** Asks the admins of a Private project for access, with an optional note. */
export const RequestAccessModal = observer(function RequestAccessModal(props: Props) {
  const { isOpen, workspaceSlug, projectId, projectName, handleClose, onRequested } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  // store hooks
  const { requestProjectAccess } = useProject();

  const close = () => {
    setMessage("");
    handleClose();
  };

  const handleSend = async () => {
    setIsSending(true);
    try {
      await requestProjectAccess(workspaceSlug, projectId, message.trim() || undefined);
      setToast({
        type: "success",
        title: t("project_components.request_access_modal.success_title"),
        message: t("project_components.request_access_modal.success_message"),
      });
      onRequested?.();
      close();
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("something_went_wrong_please_try_again"),
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
      <DialogContent size="sm">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("project_components.request_access_modal.title")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-3">
              <p className="text-13 text-secondary">
                {projectName
                  ? t("project_components.request_access_modal.description_named", { name: projectName })
                  : t("project_components.request_access_modal.description")}
              </p>
              <TextAreaGroup resize="vertical">
                <TextArea
                  size="md"
                  surface="field"
                  rows={3}
                  maxLength={MESSAGE_MAX_LENGTH}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder={t("project_components.request_access_modal.message_placeholder")}
                  aria-label={t("project_components.request_access_modal.message_placeholder")}
                />
              </TextAreaGroup>
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" label={t("cancel")} onClick={close} />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            label={
              isSending
                ? t("project_components.request_access_modal.sending")
                : t("project_components.request_access_modal.send")
            }
            onClick={handleSend}
            loading={isSending}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});
