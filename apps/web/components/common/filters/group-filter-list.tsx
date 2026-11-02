/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { getGroupFilterOptions } from "@plane/utils";
// components
import { FilterHeader, FilterOption } from "@/components/issues/issue-layouts/filters";
// hooks
import { useFilterableUserGroups } from "@/hooks/use-filterable-user-groups";

type Props = {
  appliedFilters: string[] | null;
  handleUpdate: (val: string) => void;
  searchQuery: string;
};

/**
 * The "Group" section of the module and cycle filters: "My groups", "No group" and the groups the person may
 * filter by. Renders nothing (not even its divider) when there is no group to filter by.
 */
export const FilterGroupList = observer(function FilterGroupList(props: Props) {
  const { appliedFilters, handleUpdate, searchQuery } = props;
  const { t } = useTranslation();
  // router
  const { workspaceSlug } = useParams();
  // states
  const [previewEnabled, setPreviewEnabled] = useState(true);
  // hooks
  const { groups } = useFilterableUserGroups(workspaceSlug?.toString());

  if (!groups || groups.length === 0) return null;

  const appliedFiltersCount = appliedFilters?.length ?? 0;
  const appliedFiltersSet = new Set(appliedFilters ?? []);
  const options = getGroupFilterOptions(groups, t).filter((option) =>
    option.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="py-2">
      <FilterHeader
        title={`${t("group_filter.heading")}${appliedFiltersCount > 0 ? ` (${appliedFiltersCount})` : ""}`}
        isPreviewEnabled={previewEnabled}
        handleIsPreviewEnabled={() => setPreviewEnabled(!previewEnabled)}
      />
      {previewEnabled && (
        <div>
          {options.length > 0 ? (
            options.map((option) => (
              <FilterOption
                key={option.value}
                isChecked={appliedFiltersSet.has(option.value)}
                onClick={() => handleUpdate(option.value)}
                title={option.label}
              />
            ))
          ) : (
            <p className="text-11 text-placeholder italic">{t("common.search.no_matches_found")}</p>
          )}
        </div>
      )}
    </div>
  );
});
