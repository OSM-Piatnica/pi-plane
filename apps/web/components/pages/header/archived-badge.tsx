/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { ArchiveOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
// store
import { useLocalizedDates } from "@/hooks/use-localized-dates";
import type { TPageInstance } from "@/store/pages/base-page";

type Props = {
  page: TPageInstance;
};

export const PageArchivedBadge = observer(function PageArchivedBadge({ page }: Props) {
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();
  if (!page.archived_at) return null;

  return (
    <div className="flex h-6 flex-shrink-0 items-center gap-1 rounded-sm bg-accent-primary/20 px-2 text-accent-primary">
      <ArchiveOutline className="size-3.5 flex-shrink-0" />
      <span className="text-11 font-medium">
        {t("date_phrases.archived_at", { date: formatDate(page.archived_at) })}
      </span>
    </div>
  );
});
