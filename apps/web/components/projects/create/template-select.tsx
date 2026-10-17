/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Select } from "@plane/blocks/select";
import type { TProjectTemplate } from "@plane/types";
import { ProjectTemplateService } from "@/services/project-template.service";

const projectTemplateService = new ProjectTemplateService();

export type TProjectTemplateSelect = {
  disabled?: boolean;
  value?: string | null;
  onSelect?: (templateId: string | null) => void;
};

type TOption = { id: string; name: string };

export function ProjectTemplateSelect(props: TProjectTemplateSelect) {
  const { disabled = false, value, onSelect } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { data: templates, isLoading } = useSWR(
    workspaceSlug ? `PROJECT_TEMPLATE_LIST_CREATE_${String(workspaceSlug)}` : null,
    () => projectTemplateService.list(String(workspaceSlug))
  );

  const noneOption: TOption = { id: "", name: t("project_templates.none") };
  const options: TOption[] = [
    noneOption,
    ...((templates as TProjectTemplate[] | undefined) ?? []).map((template) => ({
      id: template.id,
      name: template.name,
    })),
  ];
  const selectedOption = options.find((option) => option.id === (value ?? "")) ?? null;
  const placeholder = isLoading ? t("project_templates.loading") : t("project_templates.select_placeholder");

  return (
    <div className="min-w-[11rem]">
      <Select<TOption>
        getValues={() => options}
        value={value ? selectedOption : null}
        onChange={(next) => onSelect?.(next ? String(next) : null)}
        getOptionValue={(option) => option.id}
        getOptionLabel={(option) => option.name}
        disabled={disabled || isLoading}
        placeholder={placeholder}
        showSearch={false}
        pinSelected={false}
      >
        <Select.Trigger variant="select-md" className="w-full">
          <Select.Value />
        </Select.Trigger>
      </Select>
    </div>
  );
}
