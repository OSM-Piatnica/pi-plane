/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AlertTriangle } from "lucide-react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Checkbox } from "@makeplane/propel/components/checkbox";
import { ConfirmDialog } from "@plane/blocks/dialog";
import type { TRelationRescheduleShift } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
import { getRescheduleDependents } from "@/helpers/reschedule";
import { useWorkflow } from "@/hooks/store/use-workflow";
import { getRescheduleDeadlineWarning } from "./reschedule-deadline-warning";

const formatRange = (start: string | null, target: string | null) =>
  [start ? renderFormattedDate(start) : "…", target ? renderFormattedDate(target) : "…"].join(" – ");

function ShiftList({ shifts, muted = false }: { shifts: TRelationRescheduleShift[]; muted?: boolean }) {
  const { t } = useTranslation();
  return (
    <ul className={cn("flex max-h-60 flex-col gap-1 overflow-y-auto text-left", { "opacity-50": muted })}>
      {shifts.map((shift) => {
        const warning = getRescheduleDeadlineWarning(shift);
        return (
          <li key={shift.id} className="text-12">
            <span className="font-medium text-primary">{shift.ref}</span> {shift.name}:{" "}
            {formatRange(shift.start_date, shift.finish_date)} →{" "}
            {formatRange(shift.new_start_date, shift.new_finish_date)}
            {warning && (
              <span className="flex items-start gap-1 text-danger-primary">
                <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden />
                <span>{t(warning.key, warning.params)}</span>
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Asks whether the work items that depend on one whose dates just changed may be moved along, and whether its
 * sub-work items follow it (ticked by default), listing what would move. Mounted once; the issue store opens it when
 * the API offers the shift instead of saving the change straight away.
 */
export const RescheduleConfirmModal = observer(function RescheduleConfirmModal() {
  const { t } = useTranslation();
  const { pendingReschedule, rescheduleMoveSubItems, setRescheduleMoveSubItems, resolveReschedule } = useWorkflow();
  const offer = pendingReschedule ?? { shifts: [], sub_items: [], shifts_with_sub_items: [] };
  // a broken dependency always has dependents to move; without one only the sub-work items are offered
  const breaksDependencies = offer.shifts.length > 0;
  const dependents = getRescheduleDependents(offer, rescheduleMoveSubItems);
  const movesAnything = dependents.length > 0 || (rescheduleMoveSubItems && offer.sub_items.length > 0);

  return (
    <ConfirmDialog
      isOpen={pendingReschedule !== null}
      variant="warning"
      title={t(breaksDependencies ? "issue.relation.reschedule.title" : "issue.relation.reschedule.sub_items_title")}
      content={
        <span className="flex flex-col gap-2">
          <span>
            {t(
              breaksDependencies ? "issue.relation.reschedule.content" : "issue.relation.reschedule.sub_items_content"
            )}
          </span>
          {dependents.length > 0 && (
            <>
              {!breaksDependencies && <span>{t("issue.relation.reschedule.sub_items_dependents")}</span>}
              <ShiftList shifts={dependents} />
            </>
          )}
          {offer.sub_items.length > 0 && (
            <span className="flex flex-col gap-1 text-left">
              <Checkbox
                label={t("issue.relation.reschedule.sub_items_toggle", { count: offer.sub_items.length })}
                checked={rescheduleMoveSubItems}
                onCheckedChange={(checked) => setRescheduleMoveSubItems(checked === true)}
              />
              <ShiftList shifts={offer.sub_items} muted={!rescheduleMoveSubItems} />
            </span>
          )}
        </span>
      }
      primaryButtonText={{
        default: t(movesAnything ? "issue.relation.reschedule.confirm" : "issue.relation.reschedule.save"),
      }}
      isSubmitting={false}
      handleClose={() => resolveReschedule(false)}
      handleSubmit={() => resolveReschedule(true)}
    />
  );
});
