/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane ui
import { CyclesOutline } from "@makeplane/propel/icons";
import { Tooltip } from "@makeplane/propel/components/tooltip";
// plane utils
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
//hooks
import { useCycle } from "@/hooks/store/use-cycle";

type Props = {
  cycleId: string | undefined;
  shouldShowBorder?: boolean;
};

export const IssueBlockCycle = observer(function IssueBlockCycle({ cycleId, shouldShowBorder = true }: Props) {
  const { t } = useTranslation();
  const { getCycleById } = useCycle();

  const cycle = getCycleById(cycleId);

  return (
    <Tooltip label={t("space_text.issues.cycle_tooltip", { name: cycle?.name ?? t("space_text.issues.no_cycle") })}>
      <div
        className={cn(
          "flex h-full w-full items-center justify-between gap-1 rounded-sm px-2.5 py-1 text-11 duration-300 focus:outline-none",
          { "border-[0.5px] border-strong": shouldShowBorder }
        )}
      >
        <div className="flex w-full items-center gap-1.5 text-11">
          <CyclesOutline className="h-3 w-3 flex-shrink-0" />
          <div className="max-w-40 truncate">{cycle?.name ?? t("space_text.issues.no_cycle")}</div>
        </div>
      </div>
    </Tooltip>
  );
});
