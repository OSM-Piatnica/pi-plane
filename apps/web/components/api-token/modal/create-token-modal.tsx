/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { mutate } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
import { setToast } from "@plane/blocks/toast";
import { APITokenService } from "@plane/services";
import type { IApiToken } from "@plane/types";
import { csvDownload } from "@plane/utils";
// constants
import { API_TOKENS_LIST } from "@plane/constants";
// local imports
import { CreateApiTokenForm } from "./form";
import { GeneratedTokenDetails } from "./generated-token-details";
import { useLocalizedDates } from "@/hooks/use-localized-dates";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

// services
const apiTokenService = new APITokenService();

export function CreateApiTokenModal(props: Props) {
  const { isOpen, onClose } = props;
  // states
  const [neverExpires, setNeverExpires] = useState<boolean>(false);
  const [generatedToken, setGeneratedToken] = useState<IApiToken | null | undefined>(null);
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();

  const handleClose = () => {
    onClose();

    setTimeout(() => {
      setNeverExpires(false);
      setGeneratedToken(null);
    }, 350);
  };

  const downloadSecretKey = (data: IApiToken) => {
    const csvData = {
      [t("common.title")]: data.label,
      [t("common.description")]: data.description,
      [t("date_phrases.expiry")]: data.expired_at
        ? (formatDate(data.expired_at)?.replace(",", " ") ?? "")
        : t("date_phrases.never_expires"),
      [t("workspace_settings.settings.webhooks.secret_key.title")]: data.token ?? "",
    };

    csvDownload(csvData, `secret-key-${Date.now()}`);
  };

  const handleCreateToken = async (data: Partial<IApiToken>) => {
    // make the request to generate the token
    await apiTokenService
      .create(data)
      .then((res) => {
        setGeneratedToken(res);
        downloadSecretKey(res);

        mutate<IApiToken[]>(
          API_TOKENS_LIST,
          (prevData) => {
            if (!prevData) return;

            return [res, ...prevData];
          },
          false
        );
        return;
      })
      .catch((err) => {
        setToast({
          type: "error",
          title: t("toast.error"),
          message: err.message || err.detail,
        });

        throw err;
      });
  };

  return (
    /* Dismissed only through its own buttons, matching the modal it replaces, whose `handleClose`
       was a no-op. */
    <Dialog open={isOpen} disablePointerDismissal onOpenChange={() => {}}>
      <DialogContent size="md">
        {generatedToken ? (
          <GeneratedTokenDetails handleClose={handleClose} tokenDetails={generatedToken} />
        ) : (
          <CreateApiTokenForm
            handleClose={handleClose}
            neverExpires={neverExpires}
            toggleNeverExpires={() => setNeverExpires((prevData) => !prevData)}
            onSubmit={handleCreateToken}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
