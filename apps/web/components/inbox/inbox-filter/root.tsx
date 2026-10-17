/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { ChevronDownOutline, FilterOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
// plane imports
import { cn } from "@plane/utils";
// components
import { FiltersDropdown } from "@/components/issues/issue-layouts/filters";
// hooks
import useSize from "@/hooks/use-window-size";
// local imports
import { InboxIssueFilterSelection } from "./filters/filter-selection";
import { InboxIssueOrderByDropdown } from "./sorting/order-by";

function LargeButton() {
  const { t } = useTranslation();
  return (
    <div className={cn(getButtonStyling("secondary", "base"), "px-2 text-tertiary")}>
      <FilterOutline className="size-3" />
      <span>{t("common.filters")}</span>
      <ChevronDownOutline className="size-3" />
    </div>
  );
}

const smallButton = <FilterOutline className="size-3" />;

export function FiltersRoot() {
  const windowSize = useSize();

  return (
    <div className="relative flex items-center gap-2">
      <div>
        <FiltersDropdown
          menuButton={windowSize[0] > 1280 ? <LargeButton /> : smallButton}
          title=""
          placement="bottom-end"
        >
          <InboxIssueFilterSelection />
        </FiltersDropdown>
      </div>
      <div>
        <InboxIssueOrderByDropdown />
      </div>
    </div>
  );
}
