/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Lock } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { TIssueType } from "@plane/types";
import { WorkItemTypeMarkIcon } from "./work-item-type-mark-icon";

type TProps = {
  issueType: TIssueType;
};

/**
 * The type of a work item whose type is system-managed (approval, review): shown, not switchable.
 * The server refuses a change of such a type, so no control is offered.
 */
export function IssueTypeLockedLabel(props: TProps) {
  const { issueType } = props;
  const { t } = useTranslation();
  const hint = t("work_item_types.system_managed.tooltip");

  return (
    <Tooltip label={hint} layout="stacked">
      <span className="inline-flex h-7 max-w-full items-center gap-1.5 rounded-md border border-subtle bg-layer-1 px-2 text-13 text-secondary">
        <WorkItemTypeMarkIcon issueType={issueType} size={12} />
        <span className="truncate">{issueType.name}</span>
        <Lock className="size-3 shrink-0 text-tertiary" aria-label={hint} />
      </span>
    </Tooltip>
  );
}
