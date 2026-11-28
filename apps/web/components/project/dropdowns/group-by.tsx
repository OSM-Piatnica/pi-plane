/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
import { Button as ButtonElement } from "@makeplane/propel/elements/button";
import { ListLayoutOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TProjectGroupByOptions } from "@plane/types";

type Props = {
  onChange: (value: TProjectGroupByOptions | null) => void;
  value: TProjectGroupByOptions | null | undefined;
  isMobile?: boolean;
};

/** "Group by": one list, or a group per initiative (only offered while the Initiatives feature is on) */
export function ProjectGroupByDropdown(props: Props) {
  const { onChange, value, isMobile = false } = props;
  const { t } = useTranslation();
  const options: { key: TProjectGroupByOptions | null; label: string }[] = [
    { key: null, label: t("common.none") },
    { key: "initiative", label: t("initiatives.kind.initiative") },
  ];
  const selected = options.find((option) => option.key === (value ?? null));

  return (
    <Menu>
      <div className={isMobile ? "flex w-full justify-center" : undefined}>
        <MenuTrigger
          nativeButton={false}
          render={<ButtonElement variant="secondary" size="md" stretch="auto" render={<span />} />}
        >
          <ListLayoutOutline className="size-3.5 shrink-0" />
          {value ? `${t("common.group_by")}: ${selected?.label ?? ""}` : t("common.group_by")}
        </MenuTrigger>
      </div>
      <MenuContent side="bottom" align="end">
        {options.map((option) => (
          <MenuItem
            key={option.key ?? "none"}
            label={option.label}
            selected={option.key === (value ?? null)}
            onClick={() => onChange(option.key)}
          />
        ))}
      </MenuContent>
    </Menu>
  );
}
