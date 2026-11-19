/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Input } from "@makeplane/propel/components/input";
import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";
import { setToast } from "@plane/blocks/toast";
import { InstanceService } from "@plane/services";
import type { TInstanceServiceTokenCreated } from "@plane/types";
// hooks
import { useWorkspace } from "@/hooks/store";

type Props = {
  isOpen: boolean;
  handleClose: () => void;
  onCreated: (token: TInstanceServiceTokenCreated) => Promise<void>;
};

type TApiError = { error?: string };

const instanceService = new InstanceService();

/** Today in the browser's time zone, as the `min` of a date field: a token cannot expire in the past. */
const today = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

export const CreateBotTokenModal = observer(function CreateBotTokenModal(props: Props) {
  const { isOpen, handleClose, onCreated } = props;
  // store
  const { workspaceIds, getWorkspaceById } = useWorkspace();
  // states
  const [workspaceId, setWorkspaceId] = useState("");
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const workspaceItems: Record<string, string> = {};
  for (const id of workspaceIds) {
    const workspace = getWorkspaceById(id);
    if (workspace) workspaceItems[id] = `${workspace.name} (${workspace.slug})`;
  }
  const canSave = Boolean(workspaceId) && label.trim().length > 0 && !isSaving;

  const reset = () => {
    setWorkspaceId("");
    setLabel("");
    setDescription("");
    setExpiresOn("");
  };

  const close = () => {
    reset();
    handleClose();
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const created = await instanceService.createServiceToken({
        workspace: workspaceId,
        label: label.trim(),
        description: description.trim(),
        expired_at: expiresOn || null,
      });
      reset();
      await onCreated(created);
    } catch (error) {
      setToast({
        type: "error",
        title: "Could not create the token",
        message: (error as TApiError)?.error ?? "Something went wrong.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <DialogContent size="sm">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>Create bot token</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
                <span>Workspace</span>
                <Select
                  items={workspaceItems}
                  value={workspaceId}
                  onValueChange={(selected) => setWorkspaceId(String(selected ?? ""))}
                >
                  <SelectTrigger size="lg" placeholder="Select a workspace" />
                  <SelectContent>
                    <SelectList>
                      {Object.entries(workspaceItems).map(([value, itemLabel]) => (
                        <SelectItem key={value} value={value} label={itemLabel} size="lg" />
                      ))}
                    </SelectList>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
                <label htmlFor="bot-token-label">Name</label>
                <Input
                  id="bot-token-label"
                  size="lg"
                  maxLength={255}
                  placeholder="Microsoft 365 Copilot connector"
                  value={label}
                  onChange={(event) => setLabel(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
                <label htmlFor="bot-token-description">What it is for (optional)</label>
                <Input
                  id="bot-token-description"
                  size="lg"
                  placeholder="Graph connector sync and the MCP server"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5 text-body-sm-medium text-primary">
                <label htmlFor="bot-token-expiry">Expires on (optional)</label>
                <Input
                  id="bot-token-expiry"
                  type="date"
                  size="lg"
                  min={today()}
                  value={expiresOn}
                  onChange={(event) => setExpiresOn(event.target.value)}
                />
                <span className="text-body-xs-regular text-secondary">
                  The token works through the whole of that day. Leave empty for a token that does not expire.
                </span>
              </div>
              <p className="rounded-md bg-layer-1 p-3 text-body-xs-regular text-secondary">
                The bot joins every project of the workspace, including projects created later. It can read all work
                items, states, comments and members, but cannot change anything. It does not appear in member lists or
                pickers and cannot sign in.
              </p>
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" onClick={close} label="Cancel" />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            loading={isSaving}
            disabled={!canSave}
            onClick={() => {
              void handleSave();
            }}
            label={isSaving ? "Creating" : "Create token"}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});
