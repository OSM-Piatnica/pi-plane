/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
import { CircularProgress } from "@makeplane/propel/components/circular-progress";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { CalendarOutline, UserAltOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TInitiative, TInitiativeFormData } from "@plane/types";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
import { ListItem } from "@/components/core/list";
import { DateRangeSelect } from "@/components/dropdowns/date-select";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { getInitiativeErrorMessage, getInitiativeProgressPercentage } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useStartOfTheWeek } from "@/hooks/use-start-of-the-week";
import { InitiativeHealthBadge, InitiativeIcon, InitiativeStatusSelect } from "./properties";

type TRowProps = { workspaceSlug: string; initiative: TInitiative; nested?: boolean };

const InitiativeListRow = observer(function InitiativeListRow(props: TRowProps) {
  const { workspaceSlug, initiative, nested = false } = props;
  const parentRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const startOfTheWeek = useStartOfTheWeek();
  const { updateInitiative } = useInitiative();
  const percentage = getInitiativeProgressPercentage(initiative.progress);

  const save = (data: TInitiativeFormData) =>
    updateInitiative(workspaceSlug, initiative.id, data).catch((error: unknown) =>
      setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) })
    );

  return (
    <ListItem
      title={initiative.name}
      itemLink={`/${workspaceSlug}/initiatives/${initiative.id}`}
      parentRef={parentRef}
      isMobile={isMobile}
      className={nested ? "pl-10" : undefined}
      prependTitleElement={
        <div className="flex items-center gap-2">
          <Tooltip
            label={
              initiative.progress_is_partial
                ? t("initiatives.progress.partial_tooltip", { percentage })
                : t("initiatives.progress.tooltip", { percentage })
            }
          >
            <span className="relative grid size-[30px] place-items-center">
              <CircularProgress
                value={percentage}
                size="md"
                variant={percentage === 100 ? "success" : "brand"}
                aria-label={t("initiatives.progress.projects")}
              />
              <span className="pointer-events-none absolute text-9 text-tertiary">{`${percentage}%`}</span>
            </span>
          </Tooltip>
          <InitiativeIcon kind={initiative.kind} status={initiative.status} />
        </div>
      }
      actionableItems={
        <>
          <InitiativeHealthBadge health={initiative.health} />
          <DateRangeSelect
            variant="select-ghost-md"
            className="h-6 gap-1.5 rounded-sm border-[0.5px] border-strong text-11 text-tertiary"
            value={{ from: getDate(initiative.start_date) ?? null, to: getDate(initiative.target_date) ?? null }}
            onChange={(range) =>
              void save({
                start_date: range.from ? renderFormattedPayloadDate(range.from) : null,
                target_date: range.to ? renderFormattedPayloadDate(range.to) : null,
              })
            }
            mergeDates
            placeholder={`${t("start_date")} - ${t("target_date")}`}
            weekStartsOn={startOfTheWeek}
            icon={initiative.start_date || initiative.target_date ? undefined : <CalendarOutline aria-hidden="true" />}
          />
          <InitiativeStatusSelect value={initiative.status} onChange={(status) => void save({ status })} />
          {initiative.lead ? (
            <ButtonAvatars showTooltip userIds={initiative.lead} />
          ) : (
            <Tooltip label={t("initiatives.no_lead")}>
              <UserAltOutline className="size-4 text-tertiary" aria-label={t("initiatives.no_lead")} />
            </Tooltip>
          )}
        </>
      }
    />
  );
});

/** Goals with their initiatives, then the initiatives without a goal */
export const InitiativesList = observer(function InitiativesList(props: { workspaceSlug: string }) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const { tree } = useInitiative();

  return (
    <div className="flex size-full flex-col overflow-y-auto">
      {tree.map((node) => (
        <section key={node.goal?.id ?? "no-goal"} className="flex flex-col">
          {node.goal ? (
            <InitiativeListRow workspaceSlug={workspaceSlug} initiative={node.goal} />
          ) : (
            <h2 className="border-b border-subtle bg-layer-1 px-6 py-2 text-12 font-medium text-tertiary">
              {t("initiatives.without_goal")}
            </h2>
          )}
          {node.initiatives.map((initiative) => (
            <InitiativeListRow
              key={initiative.id}
              workspaceSlug={workspaceSlug}
              initiative={initiative}
              nested={!!node.goal}
            />
          ))}
        </section>
      ))}
    </div>
  );
});
