/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TFilterProperty, TFilterableUserGroup, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
// local imports
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import {
  createFilterConfig,
  createOperatorConfigEntry,
  getMultiSelectConfig,
  translateFilterLabel,
} from "../../../rich-filters";
import type { TGroupFilterOption } from "../../../user-group-filter";
import { getGroupFilterOptions } from "../../../user-group-filter";

// ------------ Group assignee filter ------------

/**
 * Group assignee filter specific params
 */
export type TCreateGroupAssigneeFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TGroupFilterOption> & {
    /** The groups the person may filter by. */
    groups: TFilterableUserGroup[];
  };

/**
 * Helper to get the group multi select config: "My groups" and "No group", then the groups
 * @param params - The filter params
 * @returns The group multi select config
 */
export const getGroupMultiSelectConfig = (
  params: TCreateGroupAssigneeFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<TGroupFilterOption, string, TGroupFilterOption>(
    {
      items: getGroupFilterOptions(params.groups, params.t),
      getId: (option) => option.value,
      getLabel: (option) => option.label,
      getValue: (option) => option.value,
      getIconData: (option) => option,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      ...params,
    }
  );

/**
 * Get the group assignee filter config
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the group assignee filter config
 */
export const getGroupAssigneeFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateGroupAssigneeFilterParams> =>
  (params: TCreateGroupAssigneeFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: translateFilterLabel(params.t, "group_filter.heading", "Group"),
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getGroupMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
