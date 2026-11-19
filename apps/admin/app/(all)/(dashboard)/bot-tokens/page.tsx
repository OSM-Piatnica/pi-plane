/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
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
import { setToast } from "@plane/blocks/toast";
import { InstanceService } from "@plane/services";
import type { TInstanceServiceToken, TInstanceServiceTokenCreated } from "@plane/types";
import { renderFormattedDate } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useWorkspace } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { CreateBotTokenModal } from "./create-token-modal";
import { BotTokenCreatedModal } from "./token-created-modal";

const instanceService = new InstanceService();
const BOT_TOKENS_KEY = "INSTANCE_BOT_TOKENS";

const formatDate = (value: string | null) => (value ? (renderFormattedDate(value, "MMM dd, yyyy HH:mm") ?? "") : "");

function TokenStatus({ token }: { token: TInstanceServiceToken }) {
  if (token.is_expired) return <span className="text-body-xs-medium text-danger-primary">Expired</span>;
  if (token.expired_at)
    return <span className="text-body-xs-regular text-secondary">Expires {formatDate(token.expired_at)}</span>;
  return <span className="text-body-xs-regular text-secondary">Does not expire</span>;
}

const BotTokensPage = observer(function BotTokensPage(_props: Route.ComponentProps) {
  // states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createdToken, setCreatedToken] = useState<TInstanceServiceTokenCreated | null>(null);
  const [revoking, setRevoking] = useState<TInstanceServiceToken | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  // store
  const { fetchWorkspaces } = useWorkspace();

  // the workspace list feeds the picker of the create dialog
  useSWR("INSTANCE_WORKSPACES", () => fetchWorkspaces());
  const { data: tokens, mutate } = useSWR(BOT_TOKENS_KEY, () => instanceService.serviceTokens());

  const handleRevoke = async (token: TInstanceServiceToken) => {
    setIsWorking(true);
    try {
      await instanceService.deleteServiceToken(token.id);
      await mutate();
      setRevoking(null);
      setToast({ type: "success", title: "Token revoked", message: `${token.label} no longer works.` });
    } catch {
      setToast({ type: "error", title: "Could not revoke the token", message: "Something went wrong." });
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <PageWrapper
      header={{
        title: "Bot tokens",
        description:
          "Read-only API tokens for integrations such as the Microsoft 365 Copilot connector or an MCP server. The bot of a workspace is a member of all its projects, including new ones, so its tokens read every work item, state, comment and member, but cannot change anything.",
      }}
    >
      <div className="space-y-4">
        <Button
          variant="primary"
          size="lg"
          stretch="auto"
          label="Create bot token"
          onClick={() => setIsCreateOpen(true)}
        />
        {tokens && tokens.length === 0 && <p className="text-13 text-secondary">No bot tokens yet.</p>}
        {tokens && tokens.length > 0 && (
          <ul className="divide-y divide-subtle rounded-lg border border-subtle">
            {tokens.map((token) => (
              <li key={token.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-body-sm-medium text-primary">{token.label}</span>
                    <span className="font-mono text-body-xs-regular text-tertiary">…{token.token_hint}</span>
                  </div>
                  {token.description && (
                    <span className="truncate text-body-xs-regular text-secondary">{token.description}</span>
                  )}
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-body-xs-regular text-secondary">
                    <span>
                      {token.workspace_detail?.name ?? "Deleted workspace"} · {token.project_count}{" "}
                      {token.project_count === 1 ? "project" : "projects"}
                    </span>
                    <TokenStatus token={token} />
                    <span>{token.last_used ? `Last used ${formatDate(token.last_used)}` : "Never used"}</span>
                    <span>
                      Created {formatDate(token.created_at)}
                      {token.created_by_detail ? ` by ${token.created_by_detail.display_name}` : ""}
                    </span>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  size="lg"
                  stretch="auto"
                  label="Revoke"
                  disabled={isWorking}
                  onClick={() => setRevoking(token)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
      <CreateBotTokenModal
        isOpen={isCreateOpen}
        handleClose={() => setIsCreateOpen(false)}
        onCreated={async (created) => {
          await mutate();
          setIsCreateOpen(false);
          setCreatedToken(created);
        }}
      />
      <BotTokenCreatedModal token={createdToken} handleClose={() => setCreatedToken(null)} />
      <Dialog
        open={Boolean(revoking)}
        onOpenChange={(open) => {
          if (!open) setRevoking(null);
        }}
      >
        <DialogContent size="sm">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>Revoke {revoking?.label}?</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <DialogBody>
              <p className="text-body-sm-regular text-secondary">
                Applications that use this token lose access at once. This cannot be undone: to restore access, create a
                new token and put it in their settings.
              </p>
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="md" stretch="auto" onClick={() => setRevoking(null)} label="Cancel" />
            <Button
              variant="danger"
              size="md"
              stretch="auto"
              loading={isWorking}
              disabled={isWorking}
              onClick={() => {
                if (revoking) void handleRevoke(revoking);
              }}
              label="Revoke"
            />
          </DialogActions>
        </DialogContent>
      </Dialog>
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Bot Tokens - God Mode" }];

export default BotTokensPage;
