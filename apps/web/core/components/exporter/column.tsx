/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { Download } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import type { IExportData } from "@plane/types";
import { getDate, getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// local imports
import { ImportExportStatusPill } from "./status-pill";

type RowData = IExportData;
const checkExpiry = (inputDateString: string) => {
  const currentDate = new Date();
  const expiryDate = getDate(inputDateString);
  if (!expiryDate) return false;
  expiryDate.setDate(expiryDate.getDate() + 7);
  return expiryDate > currentDate;
};
export const useExportColumns = () => {
  const { t } = useTranslation();

  const columns = [
    {
      key: "Exported By",
      content: t("workspace_settings.settings.exports.history.exported_by"),
      tdRender: (rowData: RowData) => {
        const { avatar_url, display_name, email } = rowData.initiated_by_detail;
        return (
          <div className="flex items-center gap-x-2">
            <div>
              {avatar_url && avatar_url.trim() !== "" ? (
                <span className="relative flex h-4 w-4 items-center justify-center rounded-full text-on-color capitalize">
                  <img
                    src={getFileURL(avatar_url)}
                    className="absolute top-0 left-0 h-full w-full rounded-full object-cover"
                    alt={display_name || email}
                  />
                </span>
              ) : (
                <span className="bg-gray-700 relative flex h-4 w-4 items-center justify-center rounded-full text-11 text-on-color capitalize">
                  {(email ?? display_name ?? "?")[0]}
                </span>
              )}
            </div>
            <div>{display_name}</div>
          </div>
        );
      },
    },
    {
      key: "Exported On",
      content: t("workspace_settings.settings.exports.history.exported_on"),
      tdRender: (rowData: RowData) => (
        <span>
          {renderFormattedDate(rowData.created_at)} {renderFormattedTime(rowData.created_at)}
        </span>
      ),
    },

    {
      key: "Exported projects",
      content: t("workspace_settings.settings.exports.history.projects"),
      tdRender: (rowData: RowData) => (
        <div className="text-13">
          {t("workspace_settings.settings.exports.history.project_count", { count: rowData.project.length })}
        </div>
      ),
    },
    {
      key: "Format",
      content: t("workspace_settings.settings.exports.format"),
      tdRender: (rowData: RowData) => (
        <span className="text-13">
          {rowData.provider === "csv"
            ? "CSV"
            : rowData.provider === "xlsx"
              ? "Excel"
              : rowData.provider === "json"
                ? "JSON"
                : ""}
        </span>
      ),
    },
    {
      key: "Status",
      content: t("workspace_settings.settings.exports.history.status"),
      tdRender: (rowData: RowData) => <ImportExportStatusPill status={rowData.status} />,
    },
    {
      key: "Download",
      content: t("workspace_settings.settings.exports.history.download"),
      tdRender: (rowData: RowData) =>
        checkExpiry(rowData.created_at) ? (
          <>
            {rowData.status == "completed" ? (
              <a target="_blank" href={rowData?.url} rel="noopener noreferrer">
                <button className="flex w-full items-center gap-1 font-medium text-accent-primary">
                  <Download className="h-4 w-4" />
                  <div>{t("workspace_settings.settings.exports.history.download")}</div>
                </button>
              </a>
            ) : (
              "-"
            )}
          </>
        ) : (
          <div className="text-11 text-danger-primary">{t("workspace_settings.settings.exports.history.expired")}</div>
        ),
    },
  ];
  return columns;
};
