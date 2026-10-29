/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { Control } from "react-hook-form";
import { Controller } from "react-hook-form";
// constants
import type { IWebhook } from "@plane/types";
import { Switch } from "@makeplane/propel/components/switch";
import { useTranslation } from "@plane/i18n";

interface IWebHookToggle {
  control: Control<IWebhook, any>;
}

export function WebhookToggle({ control }: IWebHookToggle) {
  const { t } = useTranslation();
  return (
    <div className="flex gap-6">
      <div className="text-13 font-medium">{t("app_text.webhooks.enable_webhook")}</div>
      <Controller
        control={control}
        name="is_active"
        render={({ field: { onChange, value } }) => (
          <Switch
            size="sm"
            checked={value}
            onCheckedChange={onChange}
            aria-label={t("app_text.webhooks.enable_webhook")}
          />
        )}
      />
    </div>
  );
}
