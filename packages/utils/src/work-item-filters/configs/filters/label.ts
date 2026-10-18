/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import type { IIssueLabel, TFilterProperty, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
// local imports
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import {
  createFilterConfig,
  getMultiSelectConfig,
  createOperatorConfigEntry,
  translateFilterLabel,
} from "../../../rich-filters";

/**
 * Label filter specific params
 */
export type TCreateLabelFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<string> & {
    labels: IIssueLabel[];
  };

/**
 * Helper to get the label multi select config
 * @param params - The filter params
 * @returns The label multi select config
 */
export const getLabelMultiSelectConfig = (params: TCreateLabelFilterParams, singleValueOperator: TSupportedOperators) =>
  getMultiSelectConfig<IIssueLabel, string, string>(
    {
      items: params.labels,
      getId: (label) => label.id,
      getLabel: (label) => label.name,
      getValue: (label) => label.id,
      getIconData: (label) => label.color,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      getOptionIcon: params.getOptionIcon,
    }
  );

/**
 * Get the label filter config
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the label filter config
 */
export const getLabelFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateLabelFilterParams> =>
  (params: TCreateLabelFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: translateFilterLabel(params.t, "common.label", "Label"),
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getLabelMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
