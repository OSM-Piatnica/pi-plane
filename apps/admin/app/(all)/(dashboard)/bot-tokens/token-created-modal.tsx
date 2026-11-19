/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
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
import { setToast } from "@plane/blocks/toast";
import type { TInstanceServiceTokenCreated } from "@plane/types";
import { copyTextToClipboard } from "@plane/utils";

type Props = {
  token: TInstanceServiceTokenCreated | null;
  handleClose: () => void;
};

/** Shows a new bot token once: it cannot be read back later. */
export function BotTokenCreatedModal(props: Props) {
  const { token, handleClose } = props;
  const [isCopied, setIsCopied] = useState(false);

  const close = () => {
    setIsCopied(false);
    handleClose();
  };

  const copy = async () => {
    if (!token) return;
    try {
      await copyTextToClipboard(token.token);
      setIsCopied(true);
      setToast({ type: "success", title: "Copied", message: "The token is in your clipboard." });
    } catch {
      setToast({ type: "error", title: "Could not copy", message: "Select the token and copy it by hand." });
    }
  };

  return (
    <Dialog
      open={Boolean(token)}
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <DialogContent size="sm">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>Copy the token now</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody>
            {token && (
              <div className="flex flex-col gap-4">
                <p className="text-body-sm-regular text-secondary">
                  This is the only time the token is shown. Store it where the application that uses it keeps its
                  secrets (for example the <code>PLANE_API_TOKEN</code> setting) and never send it by email or chat. If
                  it is lost, revoke it and create a new one.
                </p>
                <div className="flex items-center gap-2">
                  <Input
                    aria-label="Bot token"
                    size="lg"
                    readOnly
                    value={token.token}
                    onFocus={(event) => event.target.select()}
                  />
                  <Button
                    variant="primary"
                    size="lg"
                    stretch="auto"
                    label={isCopied ? "Copied" : "Copy"}
                    onClick={() => {
                      void copy();
                    }}
                  />
                </div>
                <p className="text-body-xs-regular text-secondary">
                  {token.label} reads {token.project_count} {token.project_count === 1 ? "project" : "projects"} of{" "}
                  {token.workspace_detail?.name ?? "the workspace"} now, and every project created there later.
                </p>
              </div>
            )}
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <Button variant="secondary" size="md" stretch="auto" onClick={close} label="I have copied it" />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
}
