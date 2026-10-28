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
import { setToast } from "@plane/blocks/toast";
// hooks
import { useInstance } from "@/hooks/store";

const MB = 1024 * 1024;

type TApiError = { error?: string };

export const UploadLimitSection = observer(function UploadLimitSection() {
  // store hooks
  const { config, formattedConfig, fetchInstanceConfigurations, fetchInstanceInfo, updateInstanceConfigurations } =
    useInstance();
  // states
  const [draft, setDraft] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  // derived values
  const effectiveMb = config?.file_size_limit ? Math.round(config.file_size_limit / MB) : undefined;
  const maxMb = config?.file_size_limit_max ? Math.floor(config.file_size_limit_max / MB) : undefined;
  const isCustom = Boolean(formattedConfig?.FILE_SIZE_LIMIT);
  const value = draft ?? (effectiveMb === undefined ? "" : String(effectiveMb));
  const megabytes = Number(value);
  const isValid = Number.isInteger(megabytes) && megabytes >= 1 && (maxMb === undefined || megabytes <= maxMb);
  const isChanged = draft !== undefined && draft !== String(effectiveMb);

  const save = async (limit: string) => {
    setIsSubmitting(true);
    try {
      await updateInstanceConfigurations({ FILE_SIZE_LIMIT: limit });
      await fetchInstanceInfo();
      setDraft(undefined);
      setToast({
        type: "success",
        title: "Success",
        message: limit ? "Upload limit updated" : "Upload limit set back to the default",
      });
    } catch (error) {
      setToast({
        type: "error",
        title: "Error",
        message: (error as TApiError)?.error ?? "The upload limit could not be saved",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="border-b border-subtle pb-1.5 text-16 font-medium text-primary">File uploads</div>
      <div className="flex flex-col gap-1">
        <label htmlFor="file_size_limit" className="text-13 text-tertiary">
          Largest file a person can upload (MB)
        </label>
        <div className="w-full max-w-60">
          <InputGroup size="lg">
            <Input
              id="file_size_limit"
              name="file_size_limit"
              type="number"
              size="lg"
              min={1}
              max={maxMb}
              step={1}
              value={value}
              onChange={(event) => setDraft(event.target.value)}
              aria-invalid={draft !== undefined && !isValid}
              aria-describedby="file_size_limit-description"
              disabled={isSubmitting}
            />
          </InputGroup>
        </div>
        <div id="file_size_limit-description" className="text-11 text-tertiary">
          Applies to attachments, images in descriptions, comments and pages, avatars, covers and logos
          {maxMb === undefined ? "" : `, up to ${maxMb} MB on this server`}. A smaller limit applies to new uploads
          only: files that are already stored stay as they are.
        </div>
        {draft !== undefined && !isValid && (
          <div className="text-11 text-danger-primary">
            Enter a whole number of megabytes from 1{maxMb === undefined ? "" : ` to ${maxMb}`}.
          </div>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          onClick={() => {
            void save(String(megabytes * MB));
          }}
          disabled={!isChanged || !isValid || isSubmitting}
          loading={isSubmitting}
          label={isSubmitting ? "Saving" : "Save upload limit"}
        />
        {isCustom && (
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={() => {
              void save("");
            }}
            disabled={isSubmitting}
            label="Use the default"
          />
        )}
      </div>
    </div>
  );
});
