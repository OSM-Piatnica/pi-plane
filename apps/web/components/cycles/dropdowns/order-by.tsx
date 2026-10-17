/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ArrowDownWideNarrow, ArrowUpWideNarrow } from "lucide-react";
import { CYCLE_ORDER_BY_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { CheckIcon, ChevronDownIcon } from "@plane/propel/icons";
import type { TCycleOrderByOptions } from "@plane/types";
import { CustomMenu } from "@plane/ui";
import { cn } from "@plane/utils";

type Props = {
  onChange: (value: TCycleOrderByOptions) => void;
  value: TCycleOrderByOptions | undefined;
};

export function CycleOrderByDropdown(props: Props) {
  const { onChange, value = "status" } = props;
  // hooks
  const { t } = useTranslation();

  const isDescending = value.startsWith("-");
  const currentKey = isDescending ? value.slice(1) : value;
  const orderByDetails = CYCLE_ORDER_BY_OPTIONS.find((option) => option.key === currentKey);
  // direction only makes sense for the name and start date orders
  const hasDirection = currentKey === "name" || currentKey === "start_date";

  return (
    <CustomMenu
      customButton={
        <div className={cn(getButtonStyling("secondary", "lg"), "px-2 text-tertiary")}>
          {!isDescending ? <ArrowUpWideNarrow className="size-3" /> : <ArrowDownWideNarrow className="size-3" />}
          {orderByDetails && t(orderByDetails.i18n_label)}
          <ChevronDownIcon className="size-3" strokeWidth={2} />
        </div>
      }
      placement="bottom-end"
      maxHeight="lg"
      closeOnSelect
    >
      {CYCLE_ORDER_BY_OPTIONS.map((option) => (
        <CustomMenu.MenuItem
          key={option.key}
          className="flex items-center justify-between gap-2"
          onClick={() => {
            const supportsDirection = option.key === "name" || option.key === "start_date";
            onChange(isDescending && supportsDirection ? (`-${option.key}` as TCycleOrderByOptions) : option.key);
          }}
        >
          {t(option.i18n_label)}
          {currentKey === option.key && <CheckIcon className="h-3 w-3" />}
        </CustomMenu.MenuItem>
      ))}
      {hasDirection && (
        <>
          <hr className="my-2 border-subtle" />
          <CustomMenu.MenuItem
            className="flex items-center justify-between gap-2"
            onClick={() => {
              if (isDescending) onChange(currentKey as TCycleOrderByOptions);
            }}
          >
            {t("common.order_by.asc")}
            {!isDescending && <CheckIcon className="h-3 w-3" />}
          </CustomMenu.MenuItem>
          <CustomMenu.MenuItem
            className="flex items-center justify-between gap-2"
            onClick={() => {
              if (!isDescending) onChange(`-${currentKey}` as TCycleOrderByOptions);
            }}
          >
            {t("common.order_by.desc")}
            {isDescending && <CheckIcon className="h-3 w-3" />}
          </CustomMenu.MenuItem>
        </>
      )}
    </CustomMenu>
  );
}
