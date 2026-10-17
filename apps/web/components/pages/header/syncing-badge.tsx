/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState, useEffect } from "react";
import { CloudOff, Dot } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { Badge } from "@plane/propel/badge";

type Props = {
  syncStatus: "syncing" | "synced" | "error";
};

export function PageSyncingBadge({ syncStatus }: Props) {
  const { t } = useTranslation();
  const [prevSyncStatus, setPrevSyncStatus] = useState<"syncing" | "synced" | "error" | null>(null);
  const [isVisible, setIsVisible] = useState(syncStatus !== "synced");

  useEffect(() => {
    // Only handle transitions when there's a change
    if (prevSyncStatus !== syncStatus) {
      if (syncStatus === "synced") {
        // Delay hiding to allow exit animation to complete
        setTimeout(() => {
          setIsVisible(false);
        }, 300); // match animation duration
      } else {
        setIsVisible(true);
      }
      setPrevSyncStatus(syncStatus);
    }
  }, [syncStatus, prevSyncStatus]);

  if (!isVisible || syncStatus === "synced") return null;

  const badgeContent = {
    syncing: {
      label: t("page_sync_ui.syncing"),
      tooltipLabel: `${t("page_sync_ui.syncing")} ${t("page_sync_ui.syncing_description")}`,
    },
    error: {
      label: t("page_sync_ui.connection_lost"),
      tooltipLabel: `${t("page_sync_ui.connection_lost")} ${t("page_sync_ui.connection_lost_description")}`,
    },
  };

  // The synced early-return above guarantees this key exists
  const content = badgeContent[syncStatus];

  return (
    <Tooltip label={content.tooltipLabel} layout="stacked">
      <span className="animate-quickFadeIn">
        <Badge
          variant={syncStatus === "syncing" ? "brand" : "danger"}
          size="lg"
          prependIcon={syncStatus === "syncing" ? <Dot /> : <CloudOff />}
        >
          {content.label}
        </Badge>
      </span>
    </Tooltip>
  );
}
