/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
// components
import { FilterMemberList } from "@/components/common/filters/member-filter-list";

type Props = {
  appliedFilters: string[] | null;
  handleUpdate: (val: string) => void;
  memberIds: string[] | undefined;
  searchQuery: string;
};

export const FilterMembers = observer(function FilterMembers(props: Props) {
  const { t } = useTranslation();

  return <FilterMemberList title={t("members")} {...props} />;
});
