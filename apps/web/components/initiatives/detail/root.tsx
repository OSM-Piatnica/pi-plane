/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { TextArea } from "@makeplane/propel/components/text-area";
import {
  FlagOutline,
  LeadOutline,
  StartDateOutline,
  StateOutline,
  UpdatesOutline,
  UserAltOutline,
} from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { EFileAssetType } from "@plane/types";
import type { TInitiative, TInitiativeFormData, TNameDescriptionLoader } from "@plane/types";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { DateRangeSelect } from "@/components/dropdowns/date-select";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { MemberSelect } from "@/components/dropdowns/member/member-select";
import { DescriptionInput } from "@/components/editor/rich-text/description-input";
import { getInitiativeErrorMessage } from "@/helpers/initiatives";
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { InitiativeGoalSelect } from "../goal-select";
import { InitiativeHealthBadge, InitiativeIcon, InitiativeProgress, InitiativeStatusSelect } from "../properties";
import { InitiativeEpics, InitiativeProjects } from "./links";
import { InitiativeUpdates } from "./updates";

type TProps = { workspaceSlug: string; initiative: TInitiative };

function PropertyRow(props: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  const { icon, label, children } = props;
  return (
    <div className="flex min-h-8 items-center gap-2">
      <div className="flex w-2/5 shrink-0 items-center gap-2 text-13 text-tertiary">
        {icon}
        <span>{label}</span>
      </div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function NameInput(props: { initiative: TInitiative; onSave: (name: string) => void }) {
  const { initiative, onSave } = props;
  const { t } = useTranslation();
  const [draft, setDraft] = useState<string | undefined>(undefined);
  const value = draft ?? initiative.name;
  return (
    <TextArea
      size="2xl"
      surface="inline"
      autoResize
      rows={1}
      maxLength={255}
      value={value}
      aria-label={t("initiatives.fields.name")}
      placeholder={t("initiatives.fields.name")}
      onChange={(event) => setDraft(event.target.value.replace(/\n/g, " "))}
      onBlur={() => {
        const name = value.trim();
        setDraft(undefined);
        if (name && name !== initiative.name) onSave(name);
      }}
    />
  );
}

/** The properties panel on the right, folded with the theme's `initiativesSidebarCollapsed` */
const InitiativePropertiesPanel = observer(function InitiativePropertiesPanel(
  props: TProps & { save: (data: TInitiativeFormData) => void }
) {
  const { initiative, save } = props;
  const { t } = useTranslation();
  const startOfTheWeek = useStartOfTheWeek();
  return (
    <aside
      className="flex w-full shrink-0 flex-col gap-1 overflow-y-auto border-l border-subtle px-5 py-4 md:w-[340px]"
      aria-label={t("initiatives.properties")}
    >
      <h3 className="pb-2 text-14 font-medium text-primary">{t("initiatives.properties")}</h3>
      <PropertyRow icon={<StateOutline className="size-4" />} label={t("initiatives.fields.status")}>
        <InitiativeStatusSelect
          value={initiative.status}
          onChange={(status) => save({ status })}
          variant="select-ghost-md"
        />
      </PropertyRow>
      <PropertyRow icon={<UpdatesOutline className="size-4" />} label={t("initiatives.fields.health")}>
        <InitiativeHealthBadge health={initiative.health} />
      </PropertyRow>
      <PropertyRow icon={<LeadOutline className="size-4" />} label={t("initiatives.fields.lead")}>
        <MemberSelect
          value={initiative.lead}
          onChange={(lead) => save({ lead: lead || null })}
          multiple={false}
          clearable
          placeholder={t("initiatives.no_lead")}
          variant="select-ghost-md"
        />
      </PropertyRow>
      <PropertyRow icon={<StartDateOutline className="size-4" />} label={t("initiatives.fields.dates")}>
        <DateRangeSelect
          variant="select-ghost-md"
          value={{ from: getDate(initiative.start_date) ?? null, to: getDate(initiative.target_date) ?? null }}
          onChange={(range) =>
            save({
              start_date: range.from ? renderFormattedPayloadDate(range.from) : null,
              target_date: range.to ? renderFormattedPayloadDate(range.to) : null,
            })
          }
          placeholder={`${t("start_date")} - ${t("target_date")}`}
          weekStartsOn={startOfTheWeek}
        />
      </PropertyRow>
      {initiative.kind === "initiative" && (
        <PropertyRow icon={<FlagOutline className="size-4" />} label={t("initiatives.fields.goal")}>
          <InitiativeGoalSelect
            value={initiative.parent}
            onChange={(parent) => save({ parent })}
            variant="select-ghost-md"
          />
        </PropertyRow>
      )}
      <PropertyRow icon={<UserAltOutline className="size-4" />} label={t("initiatives.fields.created_by")}>
        {initiative.created_by ? <ButtonAvatars showTooltip userIds={initiative.created_by} /> : null}
      </PropertyRow>
    </aside>
  );
});

/** A goal or an initiative: name, description, progress, links and status updates */
export const InitiativeDetailRoot = observer(function InitiativeDetailRoot(props: TProps) {
  const { workspaceSlug, initiative } = props;
  const { t } = useTranslation();
  const { initiativesSidebarCollapsed } = useAppTheme();
  const { updateInitiative, getInitiativeById } = useInitiative();
  const [, setDescriptionState] = useState<TNameDescriptionLoader>("saved");
  const isGoal = initiative.kind === "goal";

  const save = useCallback(
    (data: TInitiativeFormData) =>
      void updateInitiative(workspaceSlug, initiative.id, data).catch((error: unknown) =>
        setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) })
      ),
    [updateInitiative, workspaceSlug, initiative.id, t]
  );

  const children = initiative.initiative_ids
    .map((childId) => getInitiativeById(childId))
    .filter((child): child is TInitiative => !!child);

  return (
    <div className="flex size-full flex-col overflow-hidden md:flex-row">
      <div className="flex min-w-0 flex-1 flex-col gap-6 overflow-y-auto px-6 py-5 md:px-10">
        <div className="flex flex-col gap-1">
          <span className="flex items-center gap-1.5 text-12 text-tertiary">
            <InitiativeIcon kind={initiative.kind} status={initiative.status} />
            {t(isGoal ? "initiatives.kind.goal" : "initiatives.kind.initiative")}
          </span>
          <NameInput initiative={initiative} onSave={(name) => save({ name })} />
          <DescriptionInput
            key={initiative.id}
            entityId={initiative.id}
            workspaceSlug={workspaceSlug}
            fileAssetType={EFileAssetType.INITIATIVE_DESCRIPTION}
            initialValue={initiative.description_html}
            containerClassName="-ml-3 border-none"
            setIsSubmitting={setDescriptionState}
            placeholder={t("initiatives.description_placeholder")}
            onSubmit={async (value) => {
              await updateInitiative(workspaceSlug, initiative.id, { description_html: value.description_html });
            }}
          />
        </div>

        <section className="flex flex-col gap-4 rounded-md border border-subtle p-4">
          <InitiativeProgress
            label={t("initiatives.progress.projects")}
            progress={initiative.progress}
            isPartial={initiative.progress_is_partial}
            partialNote={t("initiatives.progress.hidden_projects", { count: initiative.hidden_project_count })}
            emptyNote={t("initiatives.progress.projects_empty")}
          />
          <InitiativeProgress
            label={t("initiatives.progress.epics")}
            progress={initiative.epic_progress}
            isPartial={initiative.epic_progress_is_partial}
            partialNote={
              initiative.hidden_epic_count > 0
                ? t("initiatives.progress.hidden_epics", { count: initiative.hidden_epic_count })
                : t("initiatives.progress.hidden_children")
            }
            emptyNote={t("initiatives.progress.epics_empty")}
          />
          <p className="text-12 text-tertiary">{t("initiatives.progress.explained")}</p>
        </section>

        {isGoal && (
          <section className="flex flex-col gap-2">
            <h3 className="text-14 font-medium text-primary">
              {t("initiatives.children.title")}
              <span className="ml-1.5 text-tertiary">{children.length}</span>
            </h3>
            {children.length === 0 ? (
              <p className="text-13 text-tertiary">{t("initiatives.children.empty")}</p>
            ) : (
              <ul className="flex flex-col divide-y divide-subtle rounded-md border border-subtle">
                {children.map((child) => (
                  <li key={child.id} className="flex items-center justify-between gap-2 px-3 py-2">
                    <Link
                      href={`/${workspaceSlug}/initiatives/${child.id}`}
                      className="flex min-w-0 items-center gap-2 text-13 text-primary hover:underline"
                    >
                      <InitiativeIcon kind={child.kind} status={child.status} />
                      <span className="truncate">{child.name}</span>
                    </Link>
                    <InitiativeHealthBadge health={child.health} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        <InitiativeProjects workspaceSlug={workspaceSlug} initiative={initiative} />
        <InitiativeEpics workspaceSlug={workspaceSlug} initiative={initiative} />
        <InitiativeUpdates key={initiative.id} workspaceSlug={workspaceSlug} initiative={initiative} />
      </div>
      {!initiativesSidebarCollapsed && (
        <InitiativePropertiesPanel workspaceSlug={workspaceSlug} initiative={initiative} save={save} />
      )}
    </div>
  );
});
