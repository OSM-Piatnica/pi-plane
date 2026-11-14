/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
// hooks
import { useInstance, useWorkspace } from "@/hooks/store";

type TApiError = { error?: string };

type TDraft = { workspaceId: string; role: string; domains: string };

const ROLE_OPTIONS: Record<string, string> = { "15": "Member", "5": "Guest" };

type TAutoJoinSelectProps = {
  label: string;
  placeholder: string;
  items: Record<string, string>;
  value: string;
  onChange: (value: string) => void;
  /** the width of the field */
  className: string;
};

/** A labelled single choice out of `items` (value to label). */
function AutoJoinSelect(props: TAutoJoinSelectProps) {
  const { label, placeholder, items, value, onChange, className } = props;

  return (
    <div className={`flex w-full flex-col gap-1 ${className}`}>
      <span className="text-13 text-tertiary">{label}</span>
      <Select items={items} value={value} onValueChange={(selected) => onChange(String(selected ?? ""))}>
        <SelectTrigger size="lg" placeholder={placeholder} />
        <SelectContent>
          <SelectList>
            {Object.entries(items).map(([itemValue, itemLabel]) => (
              <SelectItem key={itemValue} value={itemValue} label={itemLabel} size="lg" />
            ))}
          </SelectList>
        </SelectContent>
      </Select>
    </div>
  );
}

type TFormattedConfig = NonNullable<ReturnType<typeof useInstance>["formattedConfig"]>;

const readSavedSettings = (config: TFormattedConfig): TDraft => ({
  workspaceId: config.AUTO_JOIN_WORKSPACE_ID ?? "",
  role: config.AUTO_JOIN_WORKSPACE_ROLE || "15",
  domains: config.AUTO_JOIN_EMAIL_DOMAINS ?? "",
});

/** Whether joining is on, whether domains are missing and whether there is something to save. */
const getSettingsState = (saved: TDraft, value: TDraft) => {
  const isOn = Boolean(saved.workspaceId && saved.domains.trim());
  const missingDomains = Boolean(value.workspaceId) && !value.domains.trim();
  const isChanged =
    value.workspaceId !== saved.workspaceId || value.role !== saved.role || value.domains !== saved.domains;
  const canSave = Boolean(value.workspaceId) && isChanged && !missingDomains;
  return { isOn, missingDomains, canSave };
};

const getWorkspaceItems = (
  workspaceIds: string[],
  getWorkspaceById: (workspaceId: string) => { name: string; slug: string } | undefined,
  selectedWorkspaceId: string
) => {
  const items: Record<string, string> = {};
  for (const workspaceId of workspaceIds) {
    const workspace = getWorkspaceById(workspaceId);
    if (workspace) items[workspaceId] = `${workspace.name} (${workspace.slug})`;
  }
  // The saved workspace may sit on a page of the list that has not been loaded yet
  if (selectedWorkspaceId && !items[selectedWorkspaceId]) items[selectedWorkspaceId] = selectedWorkspaceId;
  return items;
};

/** The saved settings, what is being edited and how to save it; nothing while the settings are not loaded. */
const useAutoJoinWorkspaceSettings = () => {
  // store hooks
  const { formattedConfig, updateInstanceConfigurations } = useInstance();
  const { workspaceIds, getWorkspaceById } = useWorkspace();
  // states
  const [draft, setDraft] = useState<TDraft | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!formattedConfig) return undefined;

  const saved = readSavedSettings(formattedConfig);
  const value = draft ?? saved;
  const workspaceItems = getWorkspaceItems(workspaceIds, getWorkspaceById, value.workspaceId);

  const update = (changes: Partial<TDraft>) => setDraft({ ...value, ...changes });

  const save = async (payload: TDraft, message: string) => {
    setIsSubmitting(true);
    try {
      await updateInstanceConfigurations({
        AUTO_JOIN_WORKSPACE_ID: payload.workspaceId,
        AUTO_JOIN_WORKSPACE_ROLE: payload.role,
        AUTO_JOIN_EMAIL_DOMAINS: payload.domains,
      });
      setDraft(undefined);
      setToast({ type: "success", title: "Success", message });
    } catch (error) {
      setToast({
        type: "error",
        title: "Error",
        message: (error as TApiError)?.error ?? "The settings could not be saved",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return { saved, value, ...getSettingsState(saved, value), workspaceItems, isSubmitting, update, save };
};

/** The workspace that people of the company's email domains join when they sign in, without an invite. */
export const AutoJoinWorkspace = observer(function AutoJoinWorkspace() {
  const settings = useAutoJoinWorkspaceSettings();

  if (!settings) return null;

  const { saved, value, isOn, missingDomains, canSave, workspaceItems, isSubmitting, update, save } = settings;

  return (
    <div className="flex w-full flex-col gap-2 pt-2">
      <div>
        <div className="pb-1 text-16 font-medium">Add people to a workspace when they sign in</div>
        <div className="text-11 leading-5 font-regular text-tertiary">
          Everybody who signs in with an email address of these domains and has never been a member of the workspace
          joins it, also without an invite, and is not asked to create a workspace of their own. An invite still decides
          the role. People who were removed from the workspace or suspended are not added again. Leave the domains empty
          or turn this off to stop it.
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <AutoJoinSelect
          label="Workspace"
          placeholder="Select a workspace"
          items={workspaceItems}
          value={value.workspaceId}
          onChange={(workspaceId) => update({ workspaceId })}
          className="max-w-64"
        />
        <AutoJoinSelect
          label="Role"
          placeholder="Select a role"
          items={ROLE_OPTIONS}
          value={value.role}
          onChange={(role) => update({ role: role || "15" })}
          className="max-w-40"
        />
        <div className="flex w-full max-w-72 flex-col gap-1">
          <label htmlFor="AUTO_JOIN_EMAIL_DOMAINS" className="text-13 text-tertiary">
            Email domains, separated by commas
          </label>
          <InputGroup size="lg">
            <Input
              id="AUTO_JOIN_EMAIL_DOMAINS"
              name="AUTO_JOIN_EMAIL_DOMAINS"
              size="lg"
              placeholder="example.com"
              value={value.domains}
              onChange={(event) => update({ domains: event.target.value })}
              aria-invalid={missingDomains}
              disabled={isSubmitting}
            />
          </InputGroup>
        </div>
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          onClick={() => void save(value, "People of these domains now join the workspace when they sign in")}
          disabled={!canSave || isSubmitting}
          loading={isSubmitting}
          label={isSubmitting ? "Saving" : "Save"}
        />
        {isOn && (
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            onClick={() => void save({ ...saved, workspaceId: "" }, "Nobody joins a workspace at sign-in any more")}
            disabled={isSubmitting}
            label="Turn off"
          />
        )}
      </div>
      {missingDomains && (
        <div className="text-11 text-danger-primary">Enter at least one email domain, for example example.com.</div>
      )}
    </div>
  );
});
