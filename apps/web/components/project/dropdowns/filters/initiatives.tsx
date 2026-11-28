/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TInitiative } from "@plane/types";
import { PROJECT_NO_INITIATIVE } from "@plane/utils";
// components
import { InitiativeIcon } from "@/components/initiatives/properties";
import { FilterHeader, FilterOption } from "@/components/issues/issue-layouts/filters";
// hooks
import { useProjectInitiatives } from "@/hooks/use-project-initiatives";

type Props = {
  appliedFilters: string[] | null;
  handleUpdate: (val: string) => void;
  searchQuery: string;
};

/**
 * The "Initiatives" section of the project filters: "No initiative", then each goal (standing for the projects
 * of its initiatives) with its initiatives below it, then the initiatives without a goal. Renders nothing while
 * the Initiatives feature is off or the person may not read initiatives.
 */
export const FilterInitiatives = observer(function FilterInitiatives(props: Props) {
  const { appliedFilters, handleUpdate, searchQuery } = props;
  const { t } = useTranslation();
  const [previewEnabled, setPreviewEnabled] = useState(true);
  const { isEnabled, tree } = useProjectInitiatives();

  if (!isEnabled) return null;

  const query = searchQuery.toLowerCase();
  const matches = (name: string) => name.toLowerCase().includes(query);
  const applied = new Set(appliedFilters ?? []);
  const options: { item: TInitiative; nested: boolean }[] = [];
  for (const node of tree) {
    if (node.goal) options.push({ item: node.goal, nested: false });
    for (const item of node.initiatives) options.push({ item, nested: !!node.goal });
  }
  const visible = options.filter(({ item }) => matches(item.name));
  const noneLabel = t("initiatives.project_list.no_initiative");
  const showNone = matches(noneLabel);

  return (
    <div className="py-2">
      <FilterHeader
        title={`${t("initiatives.title")}${applied.size > 0 ? ` (${applied.size})` : ""}`}
        isPreviewEnabled={previewEnabled}
        handleIsPreviewEnabled={() => setPreviewEnabled(!previewEnabled)}
      />
      {previewEnabled && (
        <div>
          {showNone && (
            <FilterOption
              isChecked={applied.has(PROJECT_NO_INITIATIVE)}
              onClick={() => handleUpdate(PROJECT_NO_INITIATIVE)}
              title={noneLabel}
            />
          )}
          {visible.map(({ item, nested }) => (
            <div key={item.id} className={nested ? "pl-3" : undefined}>
              <FilterOption
                isChecked={applied.has(item.id)}
                onClick={() => handleUpdate(item.id)}
                icon={<InitiativeIcon kind={item.kind} status={item.status} className="size-3.5" />}
                title={item.name}
              />
            </div>
          ))}
          {!showNone && visible.length === 0 && (
            <p className="text-11 text-placeholder italic">{t("common.search.no_matches_found")}</p>
          )}
        </div>
      )}
    </div>
  );
});
