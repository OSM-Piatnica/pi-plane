/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TFilterProperty, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
// local imports
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import {
  createFilterConfig,
  createOperatorConfigEntry,
  getMultiSelectConfig,
  translateFilterLabel,
} from "../../../rich-filters";
import type { TRaciDepartment, TRaciFilterOption } from "../../../raci";
import { getRaciFilterOptions, getRaciFilterRole } from "../../../raci";

// ------------ RACI filters ------------

/**
 * RACI filter specific params
 */
export type TCreateRaciFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TRaciFilterOption> & {
    /** The departments of the workspace. */
    departments: TRaciDepartment[];
  };

/**
 * Helper to get the department multi select config: "My department", then the departments
 * @param params - The filter params
 * @returns The department multi select config
 */
export const getRaciMultiSelectConfig = (params: TCreateRaciFilterParams, singleValueOperator: TSupportedOperators) =>
  getMultiSelectConfig<TRaciFilterOption, string, TRaciFilterOption>(
    {
      items: getRaciFilterOptions(params.departments, params.t),
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

/** The label of a RACI filter: by the role its key stands for, or "any role". */
const getRaciFilterLabel = (key: string, t: TCreateRaciFilterParams["t"]): string => {
  const role = getRaciFilterRole(key);
  if (!role) return translateFilterLabel(t, "raci.properties.any", "Department (any RACI role)");
  return translateFilterLabel(t, `raci.properties.${role}`, `Departments: ${role}`);
};

/**
 * Get a RACI filter config: the departments with any role (key "raci_department_id") or with one role
 * (keys such as "raci_responsible_id")
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the RACI filter config
 */
export const getRaciFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateRaciFilterParams> =>
  (params: TCreateRaciFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: getRaciFilterLabel(key, params.t),
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getRaciMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
