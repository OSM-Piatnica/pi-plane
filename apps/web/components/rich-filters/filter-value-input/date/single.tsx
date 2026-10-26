/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
// plane imports
import { DateSelect } from "@/components/dropdowns/date-select";
import type { TDateFilterFieldConfig, TFilterConditionNodeForDisplay, TFilterProperty } from "@plane/types";
import { cn, getDate, renderFormattedPayloadDate } from "@plane/utils";
// hooks
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
// local imports
import { COMMON_FILTER_ITEM_BORDER_CLASSNAME, EMPTY_FILTER_PLACEHOLDER_TEXT } from "../../shared";

type TSingleDateFilterValueInputProps<P extends TFilterProperty> = {
  config: TDateFilterFieldConfig<string>;
  condition: TFilterConditionNodeForDisplay<P, string>;
  isDisabled?: boolean;
  onChange: (value: string | null | undefined) => void;
};

export const SingleDateFilterValueInput = observer(function SingleDateFilterValueInput<P extends TFilterProperty>(
  props: TSingleDateFilterValueInputProps<P>
) {
  const { config, condition, isDisabled, onChange } = props;
  // store hooks
  const startOfTheWeek = useStartOfTheWeek();
  // derived values
  const conditionValue = typeof condition.value === "string" ? condition.value : null;

  return (
    <DateSelect
      value={getDate(conditionValue) ?? null}
      onChange={(value) => {
        const formattedDate = value ? renderFormattedPayloadDate(value) : null;
        onChange(formattedDate);
      }}
      // A flat segment of the filter chip, like the property and operator segments beside it.
      className={cn("h-full max-w-none rounded-none border-0 bg-transparent text-body-xs-regular", {
        [COMMON_FILTER_ITEM_BORDER_CLASSNAME]: !isDisabled,
        "text-placeholder": !conditionValue,
      })}
      minDate={config.min}
      maxDate={config.max}
      placeholder={EMPTY_FILTER_PLACEHOLDER_TEXT}
      weekStartsOn={startOfTheWeek}
      defaultOpen={!conditionValue}
      disabled={isDisabled}
      variant="pill-lg"
    />
  );
});
