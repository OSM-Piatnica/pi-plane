/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { AddOutline, ChevronLeftOutline, ChevronRightOutline, MinusOutline } from "@makeplane/propel/icons";
import { stepZoom } from "./helpers";

export type TZoom = { fit: true } | { fit: false; scale: number };

type TDocumentPaneToolbarProps = {
  /** The scale the page is shown at, fitted or not. */
  scale: number;
  zoom: TZoom;
  /** False until the page has a size; the zoom read-out stays empty until then. */
  ready: boolean;
  disabled: boolean;
  onZoomChange: (zoom: TZoom) => void;
  /** Page picker, for PDFs only. */
  pages?: { current: number; count: number; onChange: (delta: number) => void };
};

/** Zoom (minus, read-out, plus, Fit, 100%) and, for PDFs, previous / next page. */
export function DocumentPaneToolbar(props: TDocumentPaneToolbarProps) {
  const { scale, zoom, ready, disabled, onZoomChange, pages } = props;
  const { t } = useTranslation();
  const zoomLabel = zoom.fit
    ? t("document_viewer.zoom_level_fit", { scale })
    : t("document_viewer.zoom_level", { scale });

  return (
    <div className="flex flex-wrap items-center gap-1 border-b border-subtle px-3 py-2">
      <IconButton
        variant="ghost"
        size="sm"
        icon={<Icon icon={MinusOutline} />}
        aria-label={t("document_viewer.zoom_out")}
        disabled={disabled}
        onClick={() => onZoomChange({ fit: false, scale: stepZoom(scale, -1) })}
      />
      <output className="min-w-24 text-center text-12 text-secondary tabular-nums" aria-live="polite">
        {ready ? zoomLabel : ""}
      </output>
      <IconButton
        variant="ghost"
        size="sm"
        icon={<Icon icon={AddOutline} />}
        aria-label={t("document_viewer.zoom_in")}
        disabled={disabled}
        onClick={() => onZoomChange({ fit: false, scale: stepZoom(scale, 1) })}
      />
      <Button
        variant="secondary"
        size="sm"
        stretch="auto"
        label={t("document_viewer.fit")}
        disabled={disabled}
        onClick={() => onZoomChange({ fit: true })}
      />
      <Button
        variant="secondary"
        size="sm"
        stretch="auto"
        label={t("document_viewer.actual_size")}
        disabled={disabled}
        onClick={() => onZoomChange({ fit: false, scale: 1 })}
      />
      {pages && (
        <div className="ml-auto flex items-center gap-1">
          <IconButton
            variant="ghost"
            size="sm"
            icon={<Icon icon={ChevronLeftOutline} />}
            aria-label={t("document_viewer.previous_page")}
            disabled={disabled || pages.current <= 1}
            onClick={() => pages.onChange(-1)}
          />
          <output
            className="min-w-14 text-center text-12 text-secondary tabular-nums"
            aria-live="polite"
            aria-label={t("document_viewer.page_label", { page: pages.current, count: pages.count })}
          >
            {pages.current} / {pages.count}
          </output>
          <IconButton
            variant="ghost"
            size="sm"
            icon={<Icon icon={ChevronRightOutline} />}
            aria-label={t("document_viewer.next_page")}
            disabled={disabled || pages.current >= pages.count}
            onClick={() => pages.onChange(1)}
          />
        </div>
      )}
    </div>
  );
}
