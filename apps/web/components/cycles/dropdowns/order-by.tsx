/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CYCLE_ORDER_BY_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button as ButtonElement } from "@makeplane/propel/elements/button";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@makeplane/propel/components/menu";
import { ChevronDownOutline, SortAscendingOutline, SortDescendingOutline } from "@makeplane/propel/icons";
import type { TCycleOrderByOptions } from "@plane/types";

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
    <Menu>
      {/* propel: `getButtonStyling` has no counterpart, so the trigger borrows the styled button
          element and Base UI grafts the menu behavior onto it. */}
      <MenuTrigger render={<ButtonElement variant="secondary" size="lg" stretch="auto" />}>
        {!isDescending ? <SortAscendingOutline className="size-3" /> : <SortDescendingOutline className="size-3" />}
        {orderByDetails && t(orderByDetails.i18n_label)}
        <ChevronDownOutline className="size-3" />
      </MenuTrigger>
      <MenuContent side="bottom" align="end">
        {CYCLE_ORDER_BY_OPTIONS.map((option) => (
          <MenuItem
            key={option.key}
            label={t(option.i18n_label)}
            selected={currentKey === option.key}
            onClick={() => {
              const supportsDirection = option.key === "name" || option.key === "start_date";
              onChange(isDescending && supportsDirection ? (`-${option.key}` as TCycleOrderByOptions) : option.key);
            }}
          />
        ))}
        {hasDirection && (
          <>
            <MenuSeparator />
            <MenuItem
              label={t("common.order_by.asc")}
              selected={!isDescending}
              onClick={() => {
                if (isDescending) onChange(currentKey as TCycleOrderByOptions);
              }}
            />
            <MenuItem
              label={t("common.order_by.desc")}
              selected={isDescending}
              onClick={() => {
                if (!isDescending) onChange(`-${currentKey}` as TCycleOrderByOptions);
              }}
            />
          </>
        )}
      </MenuContent>
    </Menu>
  );
}
