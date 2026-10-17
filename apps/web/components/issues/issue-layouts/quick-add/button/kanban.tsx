/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";

import { useTranslation } from "@plane/i18n";
import { AddOutline } from "@makeplane/propel/icons";
import type { TQuickAddIssueButton } from "../root";

export const KanbanQuickAddIssueButton = observer(function KanbanQuickAddIssueButton(props: TQuickAddIssueButton) {
  const { onClick, isEpic = false } = props;
  const { t } = useTranslation();
  return (
    // oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- existing markup; a11y behaviour change out of scope for lint cleanup
    <div
      className="flex w-full cursor-pointer items-center gap-2 rounded-lg bg-layer-transparent px-2 py-1 py-1.5 hover:bg-layer-transparent-hover"
      onClick={onClick}
    >
      <AddOutline className="h-3.5 w-3.5" />
      <span className="text-13 font-medium">{isEpic ? t("epic.new") : t("issue.new")}</span>
    </div>
  );
});
