/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { Control } from "react-hook-form";
import { Controller } from "react-hook-form";
import { CheckboxField } from "@makeplane/propel/components/checkbox-field";
import { useTranslation } from "@plane/i18n";
import type { IWebhook } from "@plane/types";

const INDIVIDUAL_WEBHOOK_OPTIONS: {
  key: keyof IWebhook;
  label: string;
  description: string;
}[] = [
  {
    key: "project",
    label: "projects",
    description: "project_components.webhooks.events.project",
  },
  {
    key: "cycle",
    label: "cycles",
    description: "project_components.webhooks.events.cycle",
  },
  {
    key: "issue",
    label: "work_items",
    description: "project_components.webhooks.events.issue",
  },
  {
    key: "module",
    label: "modules",
    description: "project_components.webhooks.events.module",
  },
  {
    key: "issue_comment",
    label: "project_components.webhooks.events.issue_comment_label",
    description: "project_components.webhooks.events.issue_comment",
  },
];

type Props = {
  control: Control<IWebhook, any>;
};

export function WebhookIndividualEventOptions({ control }: Props) {
  // translation
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 gap-x-4 gap-y-8 px-6 lg:grid-cols-2">
      {INDIVIDUAL_WEBHOOK_OPTIONS.map((option) => (
        <Controller
          key={option.key}
          control={control}
          name={option.key}
          render={({ field: { onChange, value } }) => (
            <CheckboxField
              name={option.key}
              label={t(option.label)}
              size="lg"
              description={t(option.description)}
              stretch="full"
              checked={value === true}
              onCheckedChange={onChange}
            />
          )}
        />
      ))}
    </div>
  );
}
