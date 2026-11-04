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

/** The workspace that people of the company's email domains join when they sign in, without an invite. */
export const AutoJoinWorkspace = observer(function AutoJoinWorkspace() {
  // store hooks
  const { formattedConfig, updateInstanceConfigurations } = useInstance();
  const { workspaceIds, getWorkspaceById } = useWorkspace();
  // states
  const [draft, setDraft] = useState<TDraft | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!formattedConfig) return null;

  const saved: TDraft = {
    workspaceId: formattedConfig.AUTO_JOIN_WORKSPACE_ID ?? "",
    role: formattedConfig.AUTO_JOIN_WORKSPACE_ROLE || "15",
    domains: formattedConfig.AUTO_JOIN_EMAIL_DOMAINS ?? "",
  };
  const value = draft ?? saved;
  const isOn = Boolean(saved.workspaceId && saved.domains.trim());
  const missingDomains = Boolean(value.workspaceId) && !value.domains.trim();
  const isChanged =
    value.workspaceId !== saved.workspaceId || value.role !== saved.role || value.domains !== saved.domains;
  const canSave = Boolean(value.workspaceId) && isChanged && !missingDomains;

  const workspaceItems: Record<string, string> = {};
  for (const workspaceId of workspaceIds) {
    const workspace = getWorkspaceById(workspaceId);
    if (workspace) workspaceItems[workspaceId] = `${workspace.name} (${workspace.slug})`;
  }
  // The saved workspace may sit on a page of the list that has not been loaded yet
  if (value.workspaceId && !workspaceItems[value.workspaceId]) workspaceItems[value.workspaceId] = value.workspaceId;

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
        <div className="flex w-full max-w-64 flex-col gap-1">
          <span className="text-13 text-tertiary">Workspace</span>
          <Select
            items={workspaceItems}
            value={value.workspaceId}
            onValueChange={(workspaceId) => update({ workspaceId: String(workspaceId ?? "") })}
          >
            <SelectTrigger size="lg" placeholder="Select a workspace" />
            <SelectContent>
              <SelectList>
                {Object.entries(workspaceItems).map(([workspaceId, label]) => (
                  <SelectItem key={workspaceId} value={workspaceId} label={label} size="lg" />
                ))}
              </SelectList>
            </SelectContent>
          </Select>
        </div>
        <div className="flex w-full max-w-40 flex-col gap-1">
          <span className="text-13 text-tertiary">Role</span>
          <Select
            items={ROLE_OPTIONS}
            value={value.role}
            onValueChange={(role) => update({ role: String(role ?? "15") })}
          >
            <SelectTrigger size="lg" placeholder="Select a role" />
            <SelectContent>
              <SelectList>
                {Object.entries(ROLE_OPTIONS).map(([role, label]) => (
                  <SelectItem key={role} value={role} label={label} size="lg" />
                ))}
              </SelectList>
            </SelectContent>
          </Select>
        </div>
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
