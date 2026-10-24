/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the hierarchy controls of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { ChevronsDownUp, ChevronsUpDown, ListTree } from "lucide-react";
// plane imports
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
import { useTranslation } from "@plane/i18n";

/** The levels offered by name; more are reached with "All levels". */
const LEVELS = [2, 3, 4];

type Props = {
  /** How many levels show by default: 1 for the top level only, null for all. */
  depth: number | null;
  onShowLevels: (depth: number | null) => void;
};

const buttonClassName =
  "flex items-center gap-1 rounded-md bg-layer-transparent p-1 px-2 text-11 hover:bg-layer-transparent-hover";

/** Unfold or fold the sub-work items of the whole timeline at once, or down to a level. */
export const GanttHierarchyControls = observer(function GanttHierarchyControls(props: Props) {
  const { depth, onShowLevels } = props;
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-1">
      <button type="button" className={buttonClassName} onClick={() => onShowLevels(null)}>
        <ChevronsUpDown className="size-3.5" />
        {t("timeline_hierarchy.expand_all")}
      </button>
      <button type="button" className={buttonClassName} onClick={() => onShowLevels(1)}>
        <ChevronsDownUp className="size-3.5" />
        {t("timeline_hierarchy.collapse_all")}
      </button>
      <Menu>
        <MenuTrigger render={<button type="button" className={buttonClassName} />}>
          <ListTree className="size-3.5" />
          {t("timeline_hierarchy.levels")}
        </MenuTrigger>
        <MenuContent side="bottom" align="end">
          {LEVELS.map((level) => (
            <MenuItem
              key={level}
              label={t("timeline_hierarchy.up_to_level", { level })}
              selected={depth === level}
              onClick={() => onShowLevels(level)}
            />
          ))}
          <MenuItem
            label={t("timeline_hierarchy.all_levels")}
            selected={depth === null}
            onClick={() => onShowLevels(null)}
          />
        </MenuContent>
      </Menu>
    </div>
  );
});
