/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
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
            type: TOAST_TYPE.INFO,
            title: t("issue.dates.notice.finish_not_defaulted"),
          });
          return;
        }
        const isDueDefaulted = notice.code === "due_date_defaulted";
        setToast({
          type: TOAST_TYPE.INFO,
          title: t(isDueDefaulted ? "issue.dates.notice.due_defaulted" : "issue.dates.notice.finish_defaulted", {
            date,
          }),
          actionItems: undo ? (
            <>
              {/* Undo is also the inline opt-out: "set only finish" / "set only due". */}
              <button
                type="button"
                className="text-13 font-medium text-primary hover:text-secondary"
                onClick={() => void undo()}
              >
                {t("issue.dates.undo")}
              </button>
            </>
          ) : undefined,
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
