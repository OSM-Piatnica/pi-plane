/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import type { TInstanceUploadConfigurationKeys } from "@plane/types";
import { setToast } from "@plane/blocks/toast";
// hooks
import { useInstance } from "@/hooks/store";

const MB = 1024 * 1024;

type TApiError = { error?: string };

type TLimitField = {
  key: TInstanceUploadConfigurationKeys;
  label: string;
  description: string;
  /** What the server uses now, in the unit of the field */
  current: number | undefined;
  max: number | undefined;
  /** Bytes are saved for sizes shown in megabytes, plain numbers for counts */
  bytesPerUnit: number;
};

type TLimitInputProps = {
  field: TLimitField;
  draft: string | undefined;
  isCustom: boolean;
  isSubmitting: boolean;
  onChange: (value: string) => void;
  onReset: () => void;
};

const isValidAmount = (value: string, max: number | undefined) => {
  const amount = Number(value);
  return value.trim() !== "" && Number.isInteger(amount) && amount >= 1 && (max === undefined || amount <= max);
};

function LimitInput(props: TLimitInputProps) {
  const { field, draft, isCustom, isSubmitting, onChange, onReset } = props;
  const value = draft ?? (field.current === undefined ? "" : String(field.current));
  const invalid = draft !== undefined && !isValidAmount(draft, field.max);
  const describedBy = `${field.key}-description`;

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={field.key} className="text-13 text-tertiary">
        {field.label}
      </label>
      <div className="flex items-center gap-3">
        <div className="w-full max-w-60">
          <InputGroup size="lg">
            <Input
              id={field.key}
              name={field.key}
              type="number"
              size="lg"
              min={1}
              max={field.max}
              step={1}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              aria-invalid={invalid}
              aria-describedby={describedBy}
              disabled={isSubmitting}
            />
          </InputGroup>
        </div>
        {isCustom && (
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={onReset}
            disabled={isSubmitting}
            label="Use the default"
          />
        )}
      </div>
      <div id={describedBy} className="text-11 text-tertiary">
        {field.description}
        {field.max === undefined ? "" : ` Up to ${field.max.toLocaleString()} here.`}
      </div>
      {invalid && (
        <div className="text-11 text-danger-primary">
          Enter a whole number from 1{field.max === undefined ? "" : ` to ${field.max.toLocaleString()}`}.
        </div>
      )}
    </div>
  );
}

export const UploadLimitSection = observer(function UploadLimitSection() {
  // store hooks
  const { config, formattedConfig, fetchInstanceConfigurations, fetchInstanceInfo, updateInstanceConfigurations } =
    useInstance();
  // states
  const [drafts, setDrafts] = useState<Partial<Record<TInstanceUploadConfigurationKeys, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const toMb = (bytes: number | undefined) => (bytes === undefined ? undefined : Math.round(bytes / MB));
  const maxMb = config?.file_size_limit_max === undefined ? undefined : Math.floor(config.file_size_limit_max / MB);

  const fields: TLimitField[] = [
    {
      key: "FILE_SIZE_LIMIT",
      label: "Largest file a person can upload (MB)",
      description:
        "Attachments, images in descriptions, comments and pages, avatars, covers and logos. A smaller limit applies to new uploads only: files that are already stored stay as they are.",
      current: toMb(config?.file_size_limit),
      max: maxMb,
      bytesPerUnit: MB,
    },
    {
      key: "IMPORT_FILE_SIZE_LIMIT",
      label: "Largest spreadsheet for a work item import (MB)",
      description: "The uploaded CSV, Excel or JSON file. It is read and imported at once and not stored.",
      current: toMb(config?.import_file_size_limit),
      max: maxMb,
      bytesPerUnit: MB,
    },
    {
      key: "IMPORT_MAX_WORK_ITEMS",
      label: "Most work items in one import",
      description: "An import runs within one request, so very large ones can time out.",
      current: config?.import_max_work_items,
      max: config?.import_max_work_items_max,
      bytesPerUnit: 1,
    },
  ];

  const changed = fields.filter((field) => {
    const draft = drafts[field.key];
    return draft !== undefined && draft !== String(field.current);
  });
  const canSave = changed.length > 0 && changed.every((field) => isValidAmount(drafts[field.key] ?? "", field.max));

  const save = async (payload: Partial<Record<TInstanceUploadConfigurationKeys, string>>, message: string) => {
    setIsSubmitting(true);
    try {
      await updateInstanceConfigurations(payload);
      await fetchInstanceInfo();
      setDrafts({});
      setToast({ type: "success", title: "Success", message });
    } catch (error) {
      setToast({
        type: "error",
        title: "Error",
        message: (error as TApiError)?.error ?? "The limits could not be saved",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="border-b border-subtle pb-1.5 text-16 font-medium text-primary">File uploads and imports</div>
      <div className="grid-col grid w-full grid-cols-1 gap-x-16 gap-y-6 lg:grid-cols-2">
        {fields.map((field) => (
          <LimitInput
            key={field.key}
            field={field}
            draft={drafts[field.key]}
            isCustom={Boolean(formattedConfig?.[field.key])}
            isSubmitting={isSubmitting}
            onChange={(value) => setDrafts((previous) => ({ ...previous, [field.key]: value }))}
            onReset={() => {
              void save({ [field.key]: "" }, "Set back to the default");
            }}
          />
        ))}
      </div>
      <div>
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          onClick={() => {
            void save(
              Object.fromEntries(
                changed.map((field) => [field.key, String(Number(drafts[field.key]) * field.bytesPerUnit)])
              ),
              "Limits updated"
            );
          }}
          disabled={!canSave || isSubmitting}
          loading={isSubmitting}
          label={isSubmitting ? "Saving" : "Save limits"}
        />
      </div>
    </div>
  );
});
