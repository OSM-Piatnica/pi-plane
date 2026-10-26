/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useFormContext } from "react-hook-form";
import { useTranslation } from "@plane/i18n";
import { Collapsible } from "@makeplane/propel/components/collapsible";
import { Switch } from "@makeplane/propel/components/switch";
import type { IProject } from "@plane/types";

type TAdvancedKey = keyof Pick<
  IProject,
  | "is_parent_completion_rule_enabled"
  | "is_blocked_status_rule_enabled"
  | "is_assignee_edit_rule_enabled"
  | "is_relation_schedule_enabled"
  | "is_relation_traceability_enabled"
  | "is_relation_relates_to_enabled"
  | "is_relation_duplicate_enabled"
>;

type TAdvancedItem = { key: TAdvancedKey; i18nPrefix: string };

const RULES: TAdvancedItem[] = [
  { key: "is_parent_completion_rule_enabled", i18nPrefix: "project_settings.workflows.rules.parent_completion" },
  { key: "is_blocked_status_rule_enabled", i18nPrefix: "project_settings.workflows.rules.blocked_status" },
  { key: "is_assignee_edit_rule_enabled", i18nPrefix: "project_settings.workflows.rules.assignee_edit" },
];

const RELATION_TYPES: TAdvancedItem[] = [
  { key: "is_relation_schedule_enabled", i18nPrefix: "project_settings.workflows.relation_types.schedule" },
  { key: "is_relation_traceability_enabled", i18nPrefix: "project_settings.workflows.relation_types.traceability" },
  { key: "is_relation_relates_to_enabled", i18nPrefix: "project_settings.workflows.relation_types.relates_to" },
  { key: "is_relation_duplicate_enabled", i18nPrefix: "project_settings.workflows.relation_types.duplicate" },
];

function AdvancedGroup({ heading, items }: { heading: string; items: TAdvancedItem[] }) {
  const { t } = useTranslation();
  const { control } = useFormContext<IProject>();

  return (
    <div>
      <p className="px-3 pt-2.5 text-12 font-medium text-tertiary">{heading}</p>
      <ul className="divide-y divide-subtle">
        {items.map((item) => (
          <li key={item.key} className="flex items-center justify-between gap-3 px-3 py-2.5">
            <div className="min-w-0">
              <p className="text-13 font-medium text-primary">{t(`${item.i18nPrefix}.title`)}</p>
              <p className="text-12 text-tertiary">{t(`${item.i18nPrefix}.description`)}</p>
            </div>
            <Controller
              name={item.key}
              control={control}
              render={({ field: { value, onChange } }) => (
                <Switch checked={Boolean(value)} onCheckedChange={onChange} size="sm" />
              )}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ProjectCreateAdvancedOptions() {
  const { t } = useTranslation();

  return (
    <div className="rounded-md border border-subtle bg-surface-1 px-3 py-2.5">
      <Collapsible
        trigger={<span className="text-13 font-medium text-primary">{t("project_create.advanced.title")}</span>}
      >
        <p className="pb-1 text-12 text-tertiary">{t("project_create.advanced.description")}</p>
        <div className="-mx-3">
          <AdvancedGroup heading={t("project_settings.workflows.rules.heading")} items={RULES} />
          <AdvancedGroup heading={t("project_settings.workflows.relation_types.heading")} items={RELATION_TYPES} />
        </div>
      </Collapsible>
    </div>
  );
}
