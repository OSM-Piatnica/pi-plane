/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TFilterProperty } from "@plane/types";
import { EQUALITY_OPERATOR } from "@plane/types";
// local imports
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import {
  createFilterConfig,
  getSingleSelectConfig,
  createOperatorConfigEntry,
  translateFilterLabel,
} from "../../../rich-filters";

// ------------ Critical path filter ------------

/**
 * The two answers of the filter: on the critical path of the schedule analysis, or not. The values are what the API
 * reads (`is_critical`).
 */
export const CRITICAL_PATH_FILTER_OPTIONS = [
  { value: "true", i18n_title: "yes", title: "Yes" },
  { value: "false", i18n_title: "no", title: "No" },
] as const;

/**
 * Critical path filter specific params
 */
export type TCreateCriticalPathFilterParams = TCreateFilterConfigParams & IFilterIconConfig<string>;

/**
 * Helper to get the critical path single select config
 * @param params - The filter params
 * @returns The critical path single select config
 */
export const getCriticalPathSingleSelectConfig = (params: TCreateCriticalPathFilterParams) =>
  getSingleSelectConfig<(typeof CRITICAL_PATH_FILTER_OPTIONS)[number], string, string>(
    {
      items: [...CRITICAL_PATH_FILTER_OPTIONS],
      getId: (option) => option.value,
      getLabel: (option) => translateFilterLabel(params.t, option.i18n_title, option.title),
      getValue: (option) => option.value,
      getIconData: (option) => option.value,
    },
    params,
    { getOptionIcon: params.getOptionIcon }
  );

/**
 * Get the critical path filter config: work items on the critical path of the schedule analysis of the project (or
 * module or cycle) of the list, or the others. Only meaningful in a list of one project.
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the critical path filter config
 */
export const getCriticalPathFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateCriticalPathFilterParams> =>
  (params: TCreateCriticalPathFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: translateFilterLabel(params.t, "schedule_analysis.critical_path", "Critical path"),
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(EQUALITY_OPERATOR.EXACT, params, (updatedParams) =>
          getCriticalPathSingleSelectConfig(updatedParams)
        ),
      ]),
    });
