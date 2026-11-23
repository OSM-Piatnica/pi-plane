/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
// plane imports
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// helpers
import { IGNORED_FILTERS_EVENT, isIgnoredFilterNoticeDue } from "@/helpers/ignored-filters.helper";

// the filters the server can leave out, and what to say about each
const NOTICES: Record<string, string> = {
  is_critical: "schedule_analysis.filter_ignored",
};

/**
 * Tells the person, in a toast, when the server left a filter out of a work item list (see
 * `helpers/ignored-filters.helper`), so a list that is not filtered by a condition they set does not pass for one
 * that is. It renders nothing. Mounted by the layouts; a list fetched again shows it at most once a minute.
 */
export function IgnoredFiltersNotice() {
  const { t } = useTranslation();
  const lastShown = useRef(new Map<string, number>());

  useEffect(() => {
    const onIgnored = (event: Event) => {
      const names = (event as CustomEvent<string[]>).detail ?? [];
      for (const name of names) {
        const key = NOTICES[name];
        if (!key || !isIgnoredFilterNoticeDue(name, lastShown.current)) continue;
        setToast({ type: "warning", title: t("warning"), message: t(key) });
      }
    };
    window.addEventListener(IGNORED_FILTERS_EVENT, onIgnored);
    return () => window.removeEventListener(IGNORED_FILTERS_EVENT, onIgnored);
  }, [t]);

  return null;
}
