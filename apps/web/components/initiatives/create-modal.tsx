/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { InputField } from "@makeplane/propel/components/input-field";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TInitiativeFormData, TInitiativeKind, TInitiativeStatus } from "@plane/types";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { DateRangeSelect } from "@/components/dropdowns/date-select";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { getInitiativeErrorMessage } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useAppRouter } from "@/hooks/use-app-router";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { InitiativeGoalSelect } from "./goal-select";
import { InitiativeStatusSelect } from "./properties";

type Props = {
  workspaceSlug: string;
  kind: TInitiativeKind;
  isOpen: boolean;
  onClose: () => void;
  /** The goal a new initiative starts under */
  parentId?: string | null;
};

const emptyForm = (kind: TInitiativeKind, parentId: string | null): TInitiativeFormData => ({
  kind,
  name: "",
  parent: kind === "initiative" ? parentId : null,
  lead: null,
  start_date: null,
  target_date: null,
  status: "planned",
});

/** Creates a goal or an initiative and opens it */
export const CreateInitiativeModal = observer(function CreateInitiativeModal(props: Props) {
  const { workspaceSlug, kind, isOpen, onClose, parentId = null } = props;
  const { t } = useTranslation();
  const router = useAppRouter();
  const startOfTheWeek = useStartOfTheWeek();
  const { createInitiative } = useInitiative();
  const [form, setForm] = useState<TInitiativeFormData>(() => emptyForm(kind, parentId));
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const change = (data: TInitiativeFormData) => setForm((current) => ({ ...current, ...data }));

  const handleClose = () => {
    onClose();
    setForm(emptyForm(kind, parentId));
    setNameError(undefined);
  };

  const handleSubmit = async () => {
    if (!form.name?.trim()) {
      setNameError(t("initiatives.form.name_required"));
      return;
    }
    setIsSubmitting(true);
    try {
      const created = await createInitiative(workspaceSlug, { ...form, kind, name: form.name.trim() });
      setToast({
        type: "success",
        title: t("toast.success"),
        message: t(kind === "goal" ? "initiatives.toast.goal_created" : "initiatives.toast.initiative_created"),
      });
      handleClose();
      router.push(`/${workspaceSlug}/initiatives/${created.id}`);
    } catch (error) {
      setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="md">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void handleSubmit();
          }}
        >
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{t(kind === "goal" ? "initiatives.new_goal" : "initiatives.new_initiative")}</DialogTitle>
              </DialogHeading>
            </DialogHeader>
            <div className="flex flex-col gap-3">
              <InputField
                size="xl"
                orientation="vertical"
                label={t("initiatives.fields.name")}
                required
                value={form.name ?? ""}
                error={nameError}
                onChange={(event) => {
                  change({ name: event.target.value });
                  if (nameError) setNameError(undefined);
                }}
                placeholder={t(kind === "goal" ? "initiatives.form.goal_placeholder" : "initiatives.form.placeholder")}
              />
              <div className="flex flex-wrap items-center gap-2">
                <InitiativeStatusSelect
                  value={form.status ?? "planned"}
                  onChange={(status: TInitiativeStatus) => change({ status })}
                />
                {kind === "initiative" && (
                  <InitiativeGoalSelect value={form.parent ?? null} onChange={(parent) => change({ parent })} />
                )}
                <MemberSelect
                  value={form.lead ?? null}
                  onChange={(lead) => change({ lead: lead || null })}
                  multiple={false}
                  clearable
                  placeholder={t("initiatives.fields.lead")}
                  variant="pill-md"
                />
                <DateRangeSelect
                  variant="pill-md"
                  value={{ from: getDate(form.start_date) ?? null, to: getDate(form.target_date) ?? null }}
                  onChange={(range) =>
                    change({
                      start_date: range.from ? renderFormattedPayloadDate(range.from) : null,
                      target_date: range.to ? renderFormattedPayloadDate(range.to) : null,
                    })
                  }
                  mergeDates
                  placeholder={`${t("start_date")} - ${t("target_date")}`}
                  weekStartsOn={startOfTheWeek}
                />
              </div>
            </div>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="sm" stretch="auto" onClick={handleClose} label={t("common.cancel")} />
            <Button
              variant="primary"
              size="sm"
              stretch="auto"
              type="submit"
              loading={isSubmitting}
              label={t(kind === "goal" ? "initiatives.create_goal" : "initiatives.create_initiative")}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
});
