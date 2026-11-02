/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { setToast } from "@plane/blocks/toast";
// hooks
import { useInstance } from "@/hooks/store";

type TApiError = { error?: string };

const isValidLimit = (value: string, max: number) => {
  const amount = Number(value);
  return value.trim() !== "" && Number.isInteger(amount) && amount >= 1 && amount <= max;
};

/** How many messages one person may send to the admins of a workspace within an hour. */
export const AdminMessageLimit = observer(function AdminMessageLimit() {
  // store hooks
  const { config, formattedConfig, fetchInstanceInfo, updateInstanceConfigurations } = useInstance();
  // states
  const [draft, setDraft] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const max = config?.admin_message_limit_max ?? 100;
  const current = config?.admin_message_limit;
  const deploymentDefault = config?.admin_message_limit_default;
  const isCustom = Boolean(formattedConfig?.ADMIN_MESSAGE_LIMIT);
  const value = draft ?? (current === undefined ? "" : String(current));
  const invalid = draft !== undefined && !isValidLimit(draft, max);
  const canSave = draft !== undefined && draft !== String(current) && !invalid;

  if (!formattedConfig || current === undefined) return null;

  const save = async (limit: string, message: string) => {
    setIsSubmitting(true);
    try {
      await updateInstanceConfigurations({ ADMIN_MESSAGE_LIMIT: limit });
      await fetchInstanceInfo();
      setDraft(undefined);
      setToast({ type: "success", title: "Success", message });
    } catch (error) {
      setToast({
        type: "error",
        title: "Error",
        message: (error as TApiError)?.error ?? "The limit could not be saved",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full flex-col gap-1">
      <label htmlFor="ADMIN_MESSAGE_LIMIT" className="pb-1 text-16 font-medium">
        Messages to the workspace admins per hour
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-full max-w-40">
          <InputGroup size="lg">
            <Input
              id="ADMIN_MESSAGE_LIMIT"
              name="ADMIN_MESSAGE_LIMIT"
              type="number"
              size="lg"
              min={1}
              max={max}
              step={1}
              value={value}
              onChange={(event) => setDraft(event.target.value)}
              aria-invalid={invalid}
              aria-describedby="ADMIN_MESSAGE_LIMIT-description"
              disabled={isSubmitting}
            />
          </InputGroup>
        </div>
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          onClick={() => void save(draft ?? "", "Limit updated")}
          disabled={!canSave || isSubmitting}
          loading={isSubmitting}
          label={isSubmitting ? "Saving" : "Save"}
        />
        {isCustom && (
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={() => void save("", "Set back to the default")}
            disabled={isSubmitting}
            label="Use the default"
          />
        )}
      </div>
      <div id="ADMIN_MESSAGE_LIMIT-description" className="text-11 leading-5 font-regular text-tertiary">
        The most messages one person can send through Help, Contact workspace admins, within an hour, in each workspace.
        The default of this installation is {deploymentDefault ?? 5}; whatever you save here replaces it. Up to {max}.
      </div>
      {invalid && <div className="text-11 text-danger-primary">Enter a whole number from 1 to {max}.</div>}
    </div>
  );
});
