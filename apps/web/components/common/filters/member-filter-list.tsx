/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { sortBy } from "lodash-es";
import { observer } from "mobx-react";
// ui
import { Avatar } from "@makeplane/propel/components/avatar";
import { Loader } from "@plane/blocks/skeleton";
import { useTranslation } from "@plane/i18n";
import { getFileURL } from "@plane/utils";
// components
import { FilterHeader, FilterOption } from "@/components/issues/issue-layouts/filters";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";

type Props = {
  /** The heading of the filter; the number of applied options is appended to it. */
  title: string;
  memberIds: string[] | undefined;
  appliedFilters: string[] | null;
  handleUpdate: (memberId: string) => void;
  searchQuery: string;
};

const INITIAL_ITEMS_TO_RENDER = 5;

/**
 * A filter section that lists workspace or project members, with the applied ones and the current user first.
 * Shared by the created-by, members and lead filters of the lists, and the inbox member filters.
 */
export const FilterMemberList = observer(function FilterMemberList(props: Props) {
  const { title, memberIds, appliedFilters, handleUpdate, searchQuery } = props;
  const { t } = useTranslation();
  // states
  const [itemsToRender, setItemsToRender] = useState(INITIAL_ITEMS_TO_RENDER);
  const [previewEnabled, setPreviewEnabled] = useState(true);
  // store hooks
  const { getUserDetails } = useMember();
  const { data: currentUser } = useUser();

  const appliedFiltersCount = appliedFilters?.length ?? 0;

  const sortedOptions = useMemo(() => {
    const filteredOptions = (memberIds || []).filter((memberId) =>
      getUserDetails(memberId)?.display_name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return sortBy(filteredOptions, [
      (memberId) => !(appliedFilters ?? []).includes(memberId),
      (memberId) => memberId !== currentUser?.id,
      (memberId) => getUserDetails(memberId)?.display_name.toLowerCase(),
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const handleViewToggle = () => {
    if (!sortedOptions) return;

    if (itemsToRender === sortedOptions.length) setItemsToRender(INITIAL_ITEMS_TO_RENDER);
    else setItemsToRender(sortedOptions.length);
  };

  const appliedFilterSet = new Set(appliedFilters);

  return (
    <>
      <FilterHeader
        title={`${title}${appliedFiltersCount > 0 ? ` (${appliedFiltersCount})` : ""}`}
        isPreviewEnabled={previewEnabled}
        handleIsPreviewEnabled={() => setPreviewEnabled(!previewEnabled)}
      />
      {previewEnabled && (
        <div>
          {sortedOptions ? (
            sortedOptions.length > 0 ? (
              <>
                {sortedOptions.slice(0, itemsToRender).map((memberId) => {
                  const member = getUserDetails(memberId);

                  if (!member) return null;
                  return (
                    <FilterOption
                      key={`member-${member.id}`}
                      isChecked={appliedFilterSet.has(member.id)}
                      onClick={() => handleUpdate(member.id)}
                      icon={
                        <Avatar
                          alt={member.display_name}
                          fallback={member.display_name?.[0]?.toUpperCase()}
                          src={getFileURL(member.avatar_url)}
                          size="xs"
                        />
                      }
                      title={currentUser?.id === member.id ? t("common.you") : member?.display_name}
                    />
                  );
                })}
                {sortedOptions.length > INITIAL_ITEMS_TO_RENDER && (
                  <button
                    type="button"
                    className="ml-8 text-11 font-medium text-accent-primary"
                    onClick={handleViewToggle}
                  >
                    {itemsToRender === sortedOptions.length
                      ? t("common.search.view_less")
                      : t("common.search.view_all")}
                  </button>
                )}
              </>
            ) : (
              <p className="text-11 text-placeholder italic">{t("common.search.no_matches_found")}</p>
            )
          ) : (
            <Loader className="space-y-2">
              <Loader.Item height="20px" />
              <Loader.Item height="20px" />
              <Loader.Item height="20px" />
            </Loader>
          )}
        </div>
      )}
    </>
  );
});
