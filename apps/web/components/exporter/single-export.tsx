/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// ui
import { Button } from "@makeplane/propel/components/button";
import { useTranslation } from "@plane/i18n";
import type { IExportData } from "@plane/types";
// helpers
import { getDate } from "@plane/utils";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
// types

type Props = {
  service: IExportData;
  refreshing: boolean;
};

export function SingleExport({ service, refreshing }: Props) {
  const provider = service.provider;
  const { formatDate } = useLocalizedDates();

  const { t } = useTranslation();
  const downloadLabel = t("workspace_settings.settings.exports.history.download");
  const statusLabels: Record<string, string> = {
    completed: t("workspace_settings.settings.exports.statuses.completed"),
    processing: t("workspace_settings.settings.exports.statuses.processing"),
    failed: t("workspace_settings.settings.exports.statuses.failed"),
    expired: t("workspace_settings.settings.exports.statuses.expired"),
  };

  const checkExpiry = (inputDateString: string) => {
    const currentDate = new Date();
    const expiryDate = getDate(inputDateString);
    if (!expiryDate) return false;
    expiryDate.setDate(expiryDate.getDate() + 7);
    return expiryDate > currentDate;
  };

  return (
    <div className="flex items-center justify-between gap-2 px-4 py-3">
      <div>
        <h4 className="flex items-center gap-2 text-13">
          <span>
            {t("workspace_settings.settings.exports.modal.title")}{" "}
            <span className="font-medium">
              {provider === "csv" ? "CSV" : provider === "xlsx" ? "Excel" : provider === "json" ? "JSON" : ""}
            </span>{" "}
          </span>
          <span
            className={`rounded-sm px-2 py-0.5 text-11 capitalize ${
              service.status === "completed"
                ? "bg-success-subtle text-success-primary"
                : service.status === "processing"
                  ? "bg-yellow-500/20 text-yellow-500"
                  : service.status === "failed"
                    ? "bg-danger-subtle text-danger-primary"
                    : service.status === "expired"
                      ? "bg-orange-500/20 text-orange-500"
                      : ""
            }`}
          >
            {refreshing ? `${t("refreshing")}...` : (statusLabels[service.status] ?? service.status)}
          </span>
        </h4>
        <div className="mt-2 flex items-center gap-2 text-11 text-secondary">
          <span>{formatDate(service.created_at)}</span>|
          <span>
            {t("workspace_settings.settings.exports.history.exported_by")} {service?.initiated_by_detail?.display_name}
          </span>
        </div>
      </div>
      {checkExpiry(service.created_at) ? (
        <>
          {service.status == "completed" && (
            <div>
              <Button
                variant="primary"
                size="sm"
                stretch="full"
                label={downloadLabel}
                nativeButton={false}
                render={
                  <a target="_blank" href={service?.url} rel="noopener noreferrer">
                    {downloadLabel}
                  </a>
                }
              />
            </div>
          )}
        </>
      ) : (
        <div className="text-11 text-danger-primary">{t("date_phrases.expired")}</div>
      )}
    </div>
  );
}
