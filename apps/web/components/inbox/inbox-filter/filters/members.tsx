/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import type { TInboxIssueFilterMemberKeys } from "@plane/types";
// components
import { FilterMemberList } from "@/components/common/filters/member-filter-list";
// hooks
import { useProjectInbox } from "@/hooks/store/use-project-inbox";

type Props = {
  filterKey: TInboxIssueFilterMemberKeys;
  label?: string;
  memberIds: string[] | undefined;
  searchQuery: string;
};

export const FilterMember = observer(function FilterMember(props: Props) {
  const { filterKey, label, memberIds, searchQuery } = props;
  // hooks
  const { t } = useTranslation();
  const { inboxFilters, handleInboxIssueFilters } = useProjectInbox();
  // derived values
  const filterValue = inboxFilters?.[filterKey] || [];

  const handleFilterValue = (value: string): string[] =>
    filterValue?.includes(value) ? filterValue.filter((v) => v !== value) : [...filterValue, value];

  return (
    <FilterMemberList
      title={label ?? t("members")}
      memberIds={memberIds}
      appliedFilters={filterValue}
      handleUpdate={(memberId) => handleInboxIssueFilters(filterKey, handleFilterValue(memberId))}
      searchQuery={searchQuery}
    />
  );
});
