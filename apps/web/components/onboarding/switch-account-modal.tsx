/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";

import { useTheme } from "next-themes";
// ui
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
// hooks
import { useUser } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { useTranslation } from "@plane/i18n";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function SwitchAccountModal(props: Props) {
  const { isOpen, onClose } = props;
  // plane hooks
  const { t } = useTranslation();
  // states
  const [switchingAccount, setSwitchingAccount] = useState(false);
  // router
  const router = useAppRouter();
  // store hooks
  const { data: userData, signOut } = useUser();

  const { setTheme } = useTheme();

  const handleClose = () => {
    setSwitchingAccount(false);
    onClose();
  };

  const handleSwitchAccount = async () => {
    setSwitchingAccount(true);

    try {
      await signOut();
      setTheme("system");
      router.push("/");
      handleClose();
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("onboarding.switch_account.toast.sign_out_failed"),
      });
    } finally {
      setSwitchingAccount(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={handleClose}
      handleSubmit={handleSwitchAccount}
      isSubmitting={switchingAccount}
      variant="primary"
      title={t("onboarding.switch_account.title")}
      content={
        userData?.email ? (
          <>
            {t("onboarding.switch_account.description_prefix")}{" "}
            <span className="text-accent-primary">{userData.email}</span>{" "}
            {t("onboarding.switch_account.description_suffix")}
          </>
        ) : null
      }
      primaryButtonText={{
        loading: t("onboarding.switch_account.switching"),
        default: t("onboarding.switch_account.title"),
      }}
    />
  );
}
