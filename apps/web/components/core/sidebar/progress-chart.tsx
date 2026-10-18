/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
// plane imports
import { AreaChart } from "@plane/blocks/charts/area-chart";
import type { TChartData, TModuleCompletionChartDistribution } from "@plane/types";
import { useTranslation } from "@plane/i18n";
import { renderFormattedDateWithoutYear } from "@plane/utils";
// hooks
import { useLocalizedDates } from "@/hooks/use-localized-dates";

type Props = {
  distribution: TModuleCompletionChartDistribution;
  totalIssues: number;
  className?: string;
  plotTitle?: string;
};

function ProgressChart({ distribution, totalIssues, className = "", plotTitle }: Props) {
  const { t } = useTranslation();
  const { locale } = useLocalizedDates();
  const title = plotTitle ?? t("work_items");
  const chartData: TChartData<string, string>[] = Object.keys(distribution ?? []).map((key, index) => ({
    name: renderFormattedDateWithoutYear(key, locale),
    current: distribution[key] ?? 0,
    ideal: totalIssues * (1 - index / (Object.keys(distribution ?? []).length - 1)),
  }));

  return (
    <div className={`flex w-full items-center justify-center ${className}`}>
      <AreaChart
        data={chartData}
        areas={[
          {
            key: "current",
            label: t("progress_chart.current", { title }),
            strokeColor: "#3F76FF",
            fill: "#3F76FF33",
            fillOpacity: 1,
            showDot: true,
            smoothCurves: true,
            strokeOpacity: 1,
            stackId: "bar-one",
          },
          {
            key: "ideal",
            label: t("progress_chart.ideal", { title }),
            strokeColor: "#A9BBD0",
            fill: "#A9BBD0",
            fillOpacity: 0,
            showDot: true,
            smoothCurves: true,
            strokeOpacity: 1,
            stackId: "bar-two",
            style: {
              strokeDasharray: "6, 3",
              strokeWidth: 1,
            },
          },
        ]}
        xAxis={{ key: "name", label: t("date") }}
        yAxis={{ key: "current", label: t("common.completion") }}
        margin={{ bottom: 30 }}
        className="h-[370px] w-full"
        legend={{
          align: "center",
          verticalAlign: "bottom",
          layout: "horizontal",
          wrapperStyles: {
            marginTop: 20,
          },
        }}
      />
    </div>
  );
}

export default ProgressChart;
