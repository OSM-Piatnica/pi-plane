/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import type { TPairedDateNotice } from "@plane/utils";
import { renderFormattedDate } from "@plane/utils";

/**
 * When the server fills a work item's other planning date for the first finish/due entry (or
 * explains why it did not), the store reports it here and the toast below tells the user, with Undo.
 * A tiny bus keeps the MobX store free of React and translations.
 */
export type TWorkItemDateNoticeEvent = {
  issueId: string;
  notices: TPairedDateNotice[];
  /** Reverts only the defaulted field, leaving the user's own edit in place. */
  undo?: () => Promise<void>;
};

type TListener = (event: TWorkItemDateNoticeEvent) => void;

const listeners = new Set<TListener>();

export const emitWorkItemDateNotice = (event: TWorkItemDateNoticeEvent) => {
  listeners.forEach((listener) => listener(event));
};

/** Mounted once next to the global `Toast`. */
export function WorkItemDateNoticeToaster() {
  const { t } = useTranslation();

  useEffect(() => {
    const listener: TListener = ({ notices, undo }) => {
      notices.forEach((notice) => {
        const date = renderFormattedDate(notice.date) ?? notice.date;
        if (notice.code === "finish_date_not_defaulted") {
          setToast({
            type: "info",
            title: t("issue.dates.notice.finish_not_defaulted"),
          });
          return;
        }
        const isDueDefaulted = notice.code === "due_date_defaulted";
        setToast({
          type: "info",
          title: t(isDueDefaulted ? "issue.dates.notice.due_defaulted" : "issue.dates.notice.finish_defaulted", {
            date,
          }),
          // Undo is also the inline opt-out: "set only finish" / "set only due".
          actionItems: undo ? [{ label: t("issue.dates.undo"), onClick: () => void undo() }] : undefined,
        });
      });
    };
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, [t]);

  return null;
}
