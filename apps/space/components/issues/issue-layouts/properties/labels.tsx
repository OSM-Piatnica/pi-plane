/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { LabelsOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
// plane imports
import { Tooltip } from "@makeplane/propel/components/tooltip";
// hooks
import { useLabel } from "@/hooks/store/use-label";

type Props = {
  labelIds: string[];
  shouldShowLabel?: boolean;
};

export const IssueBlockLabels = observer(function IssueBlockLabels({ labelIds, shouldShowLabel = false }: Props) {
  const { t } = useTranslation();
  const { getLabelsByIds } = useLabel();

  const labels = getLabelsByIds(labelIds);

  const labelsString =
    labels.length > 0 ? labels.map((label) => label.name).join(", ") : t("space_text.issues.no_labels");

  if (labels.length <= 0)
    return (
      <Tooltip side="top" label={t("space_text.issues.labels_tooltip", { labels: t("common.none") })}>
        <div
          className={`flex h-full items-center justify-center gap-2 rounded-sm border-[0.5px] border-strong px-2.5 py-1 text-11`}
        >
          <LabelsOutline className="h-3.5 w-3.5" />
          {shouldShowLabel && <span>{t("space_text.issues.no_labels")}</span>}
        </div>
      </Tooltip>
    );

  return (
    <div className="flex h-5 w-full flex-wrap items-center gap-2 overflow-hidden">
      {labels.length <= 2 ? (
        <>
          {labels.map((label) => (
            <Tooltip
              key={label.id}
              side="top"
              label={t("space_text.issues.labels_tooltip", { labels: label?.name ?? "" })}
            >
              <div
                key={label?.id}
                className={`flex h-full max-w-full flex-shrink-0 items-center overflow-hidden rounded-sm border-[0.5px] border-strong px-2.5 py-1 text-11`}
              >
                <div className="flex max-w-full items-center gap-1.5 overflow-hidden text-secondary">
                  <span
                    className="h-2 w-2 flex-shrink-0 rounded-full"
                    style={{
                      backgroundColor: label?.color ?? "#000000",
                    }}
                  />
                  <div className="line-clamp-1 inline-block w-auto max-w-[100px] truncate">{label?.name}</div>
                </div>
              </div>
            </Tooltip>
          ))}
        </>
      ) : (
        <div
          className={`cursor-not-allowed" flex h-full flex-shrink-0 items-center rounded-sm border-[0.5px] border-strong px-2.5 py-1 text-11`}
        >
          <Tooltip side="top" label={t("space_text.issues.labels_tooltip", { labels: labelsString })}>
            <div className="flex h-full items-center gap-1.5 text-secondary">
              <span className="h-2 w-2 flex-shrink-0 rounded-full bg-accent-primary" />
              {t("space_text.issues.labels_count", { count: labels.length })}
            </div>
          </Tooltip>
        </div>
      )}
    </div>
  );
});
