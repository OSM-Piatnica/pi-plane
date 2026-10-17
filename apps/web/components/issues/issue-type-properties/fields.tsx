/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Switch } from "@makeplane/propel/components/switch";
import { DateSelect } from "@/components/dropdowns/date-select";
import { Select } from "@plane/blocks/select";
import type { TIssueTypePropertyValueEntry } from "@plane/types";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { useUserProfile } from "@/hooks/store/user";

type TProps = {
  property: TIssueTypePropertyValueEntry;
  value: unknown;
  error?: string;
  disabled?: boolean;
  workspaceSlug: string;
  projectId: string;
  onChange: (value: unknown) => void;
  compact?: boolean;
};

export const IssueTypePropertyField = observer(function IssueTypePropertyField(props: TProps) {
  const { property, value, error, disabled, projectId, onChange, compact } = props;
  const { t } = useTranslation();
  const { data: userProfile } = useUserProfile();
  const type = property.property_type ?? "text";

  const label = (
    <div className={compact ? "min-w-0" : "space-y-0.5"}>
      <p className="text-12 text-tertiary">
        {property.title}
        {property.is_mandatory ? " *" : ""}
      </p>
      {error ? <p className="text-11 text-danger-primary">{error}</p> : null}
    </div>
  );

  const field = (() => {
    if (type === "boolean") {
      return (
        <Switch checked={Boolean(value)} onCheckedChange={(next) => onChange(next)} disabled={disabled} size="sm" />
      );
    }
    if (type === "number") {
      return (
        <InputGroup size="lg">
          <Input
            size="lg"
            type="number"
            value={value === null || value === undefined ? "" : String(value)}
            onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
            disabled={disabled}
          />
        </InputGroup>
      );
    }
    if (type === "date") {
      const dateValue =
        value instanceof Date ? value.toISOString().slice(0, 10) : typeof value === "string" ? value : null;
      return (
        <DateSelect
          value={getDate(dateValue) ?? null}
          onChange={(next) => onChange(next ? (renderFormattedPayloadDate(next) ?? null) : null)}
          placeholder={t("start_date")}
          weekStartsOn={userProfile?.start_of_the_week}
          variant="select-lg"
          disabled={disabled}
        />
      );
    }
    if (type === "dropdown") {
      const options = property.options ?? [];
      if (property.select_mode === "multi") {
        const selected = Array.isArray(value) ? value.map(String) : [];
        return (
          <div className="flex flex-wrap gap-1">
            {options.map((opt) => {
              const active = selected.includes(opt);
              return (
                <button
                  key={opt}
                  type="button"
                  disabled={disabled}
                  className={`rounded border px-2 py-0.5 text-12 ${
                    active ? "border-accent-primary bg-accent-primary/10 text-primary" : "border-subtle text-secondary"
                  }`}
                  onClick={() => {
                    const next = active ? selected.filter((v) => v !== opt) : [...selected, opt];
                    onChange(next);
                  }}
                >
                  {opt}
                </button>
              );
            })}
          </div>
        );
      }
      return (
        <Select<string>
          getValues={() => options}
          value={typeof value === "string" && value ? value : null}
          onChange={(next) => onChange(next || null)}
          getOptionValue={(option) => option}
          getOptionLabel={(option) => option}
          disabled={disabled}
          showSearch={false}
          pinSelected={false}
        >
          <Select.Trigger<string> variant="select-lg" className="w-full">
            <Select.Value placeholder={t("select")} />
          </Select.Trigger>
        </Select>
      );
    }
    if (type === "member_picker") {
      const memberValue = Array.isArray(value) ? value[0] : typeof value === "string" ? value : null;
      return (
        <MemberSelect
          projectId={projectId}
          value={memberValue}
          onChange={(memberId) => onChange(memberId ? [memberId] : [])}
          variant="select-lg"
          disabled={disabled}
        />
      );
    }
    return (
      <InputGroup size="lg">
        <Input
          size="lg"
          value={value === null || value === undefined ? "" : String(value)}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      </InputGroup>
    );
  })();

  if (compact) {
    return (
      <div className="space-y-1">
        {label}
        {field}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-2 py-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] md:items-center">
      {label}
      <div>{field}</div>
    </div>
  );
});
