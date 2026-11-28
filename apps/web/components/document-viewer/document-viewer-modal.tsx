/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { Button } from "@makeplane/propel/components/button";
import { Dialog, DialogClose, DialogContent, DialogTitle } from "@makeplane/propel/components/dialog";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { CloseOutline, DownloadOutline, TwoColumnsOutline } from "@makeplane/propel/icons";
import { DocumentPane } from "./document-pane";
import { DocumentThumbnail } from "./document-thumbnail";
import type { TDocumentOverlayRenderer, TDocumentSource } from "./types";

type TDocumentViewerModalProps = {
  isOpen: boolean;
  onClose: () => void;
  source: TDocumentSource;
  /** Other files that can be compared side by side with `source`, e.g. earlier versions. */
  compareCandidates?: TDocumentSource[];
  /** Layer over the main page (annotations, C3). Compare panes never get it: they are read-only. */
  renderOverlay?: TDocumentOverlayRenderer;
};

type TMode = { kind: "single" } | { kind: "pick" } | { kind: "compare"; other: TDocumentSource };

const downloadUrlOf = (source: TDocumentSource): string | undefined => source.downloadUrl ?? source.url;

function SourceHeading(props: { source: TDocumentSource }) {
  const { source } = props;
  return (
    <div className="min-w-0">
      <p className="truncate text-13 font-medium text-primary">{source.name}</p>
      {source.caption && <p className="truncate text-11 text-tertiary">{source.caption}</p>}
    </div>
  );
}

/**
 * Full-window viewer for one file, with "Compare" to show it next to another file in two
 * independent panels. Both panels render the original files.
 */
export function DocumentViewerModal(props: TDocumentViewerModalProps) {
  const { isOpen, onClose, source, compareCandidates = [], renderOverlay } = props;
  const { t } = useTranslation();
  const [mode, setMode] = useState<TMode>({ kind: "single" });
  const candidates = compareCandidates.filter((candidate) => candidate.id !== source.id);
  const downloadUrl = downloadUrlOf(source);

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          setMode({ kind: "single" });
          onClose();
        }
      }}
    >
      <DialogContent size="full" density="compact">
        <div className="flex h-full min-h-0 flex-col">
          <div className="flex items-center gap-3 border-b border-subtle px-4 py-3">
            <div className="min-w-0 flex-1">
              <DialogTitle>{source.name}</DialogTitle>
              {source.caption && <p className="truncate text-11 text-tertiary">{source.caption}</p>}
            </div>
            {candidates.length > 0 && (
              <Button
                variant={mode.kind === "single" ? "secondary" : "primary"}
                size="sm"
                stretch="auto"
                icon={<Icon icon={TwoColumnsOutline} />}
                label={mode.kind === "single" ? t("document_viewer.compare") : t("document_viewer.close_compare")}
                onClick={() => setMode(mode.kind === "single" ? { kind: "pick" } : { kind: "single" })}
              />
            )}
            {downloadUrl && (
              <AnchorButton
                variant="secondary"
                size="sm"
                icon={<Icon icon={DownloadOutline} />}
                label={t("document_viewer.download")}
                href={downloadUrl}
                external
              />
            )}
            <IconButton
              variant="ghost"
              size="sm"
              aria-label={t("close")}
              icon={<Icon icon={CloseOutline} />}
              render={<DialogClose />}
            />
          </div>

          {mode.kind === "single" && (
            <div className="min-h-0 flex-1">
              <DocumentPane key={source.id} source={source} renderOverlay={renderOverlay} />
            </div>
          )}

          {mode.kind === "pick" && (
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <p className="mb-3 text-13 text-secondary">{t("document_viewer.compare_pick")}</p>
              <ul className="grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-3">
                {candidates.map((candidate) => (
                  <li key={candidate.id}>
                    <button
                      type="button"
                      className="flex w-full flex-col items-center gap-2 rounded-md border border-subtle p-2 text-left hover:bg-layer-1"
                      onClick={() => setMode({ kind: "compare", other: candidate })}
                    >
                      <DocumentThumbnail source={candidate} size={136} />
                      <span className="w-full">
                        <SourceHeading source={candidate} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {mode.kind === "compare" && (
            <div className="grid min-h-0 flex-1 grid-rows-2 divide-subtle max-md:divide-y md:grid-cols-2 md:grid-rows-1 md:divide-x">
              {[source, mode.other].map((panel) => (
                <div key={panel.id} className="flex min-h-0 min-w-0 flex-col">
                  <div className="border-b border-subtle px-3 py-2">
                    <SourceHeading source={panel} />
                  </div>
                  <div className="min-h-0 flex-1">
                    <DocumentPane source={panel} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
