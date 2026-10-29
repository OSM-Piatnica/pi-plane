/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { renderFormattedDate } from "@plane/utils";
import { useWorkflow } from "@/hooks/store/use-workflow";

const formatRange = (start: string | null, target: string | null) =>
  [start ? renderFormattedDate(start) : "…", target ? renderFormattedDate(target) : "…"].join(" – ");

/**
 * Asks whether the work items that depend on one whose dates just changed may be moved along, listing what would
 * move. Mounted once; the issue store opens it when the API offers the shift instead of refusing the change.
 */
export const RescheduleConfirmModal = observer(function RescheduleConfirmModal() {
  const { t } = useTranslation();
  const { pendingReschedule, resolveReschedule } = useWorkflow();
  const shifts = pendingReschedule ?? [];

  return (
    <ConfirmDialog
      isOpen={pendingReschedule !== null}
      variant="warning"
      title={t("issue.relation.reschedule.title")}
      content={
        <span className="flex flex-col gap-2">
          <span>{t("issue.relation.reschedule.content")}</span>
          <ul className="flex max-h-60 flex-col gap-1 overflow-y-auto text-left">
            {shifts.map((shift) => (
              <li key={shift.id} className="text-12">
                <span className="font-medium text-primary">{shift.ref}</span> {shift.name}:{" "}
                {formatRange(shift.start_date, shift.finish_date)} →{" "}
                {formatRange(shift.new_start_date, shift.new_finish_date)}
              </li>
            ))}
          </ul>
        </span>
      }
      primaryButtonText={{ default: t("issue.relation.reschedule.confirm") }}
      isSubmitting={false}
      handleClose={() => resolveReschedule(false)}
      handleSubmit={() => resolveReschedule(true)}
    />
  );
});
