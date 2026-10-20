/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { TransferWorkItemOutline, WarningCircleOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";

type Props = {
  handleClick: () => void;
  canTransferIssues?: boolean;
  disabled?: boolean;
};

export function TransferIssues(props: Props) {
  const { t } = useTranslation();
  const { handleClick, canTransferIssues = false, disabled = false } = props;
  return (
    <div className="-mt-2 mb-4 flex items-center justify-between px-4 pt-6">
      <div className="flex items-center gap-2 text-13 text-secondary">
        <WarningCircleOutline className="h-3.5 w-3.5 text-secondary" />
        <span>{t("cycle_ui.completed_not_editable")}</span>
      </div>

      {canTransferIssues && (
        <div>
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            icon={<Icon icon={TransferWorkItemOutline} />}
            iconPosition="start"
            onClick={handleClick}
            disabled={disabled}
            label={t("cycle_ui.transfer_title")}
          />
        </div>
      )}
    </div>
  );
}
