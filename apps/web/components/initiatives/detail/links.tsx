/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Icon } from "@makeplane/propel/components/icon";
import { LinearProgress } from "@makeplane/propel/components/linear-progress";
import { AddOutline, EpicOutline, UnlinkOutline } from "@makeplane/propel/icons";
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { Select } from "@plane/blocks/select";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TInitiative, TInitiativeEpic, TInitiativeEpicOption } from "@plane/types";
import { ProjectSelect } from "@/components/dropdowns/project/project-select";
import { canLinkInProject, getInitiativeErrorMessage, getInitiativeProgressPercentage } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";

type TProps = { workspaceSlug: string; initiative: TInitiative };

function useLinkPermission(workspaceSlug: string) {
  const { getWorkspaceRoleByWorkspaceSlug, getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  const workspaceRole = getWorkspaceRoleByWorkspaceSlug(workspaceSlug);
  return (projectId: string) =>
    canLinkInProject(workspaceRole, getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId));
}

function SectionHeading(props: { title: string; count?: number; action?: React.ReactNode }) {
  const { title, count, action } = props;
  return (
    <div className="flex items-center justify-between gap-2">
      <h3 className="text-14 font-medium text-primary">
        {title}
        {count !== undefined && <span className="ml-1.5 text-tertiary">{count}</span>}
      </h3>
      {action}
    </div>
  );
}

function HiddenNote({ text }: { text: string | undefined }) {
  if (!text) return null;
  return <p className="text-12 text-tertiary">{text}</p>;
}

/** The linked projects; on an initiative they can be added and removed, a goal shows those of its initiatives */
export const InitiativeProjects = observer(function InitiativeProjects(props: TProps) {
  const { workspaceSlug, initiative } = props;
  const { t } = useTranslation();
  const { getProjectById } = useProject();
  const { linkProjects, unlinkProject } = useInitiative();
  const canLink = useLinkPermission(workspaceSlug);
  const isInitiative = initiative.kind === "initiative";

  const fail = (error: unknown) =>
    setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) });

  return (
    <section className="flex flex-col gap-2">
      <SectionHeading
        title={t("initiatives.projects.title")}
        count={initiative.project_ids.length}
        action={
          isInitiative && (
            <ProjectSelect
              multiple
              projectList="all"
              value={[]}
              onChange={(projectIds) => {
                if (projectIds.length > 0) void linkProjects(workspaceSlug, initiative.id, projectIds).catch(fail);
              }}
              filterOption={(projectId) => !initiative.project_ids.includes(projectId) && canLink(projectId)}
              placeholder={t("initiatives.projects.add")}
              variant="pill-md"
            />
          )
        }
      />
      {!isInitiative && <p className="text-12 text-tertiary">{t("initiatives.projects.of_goal")}</p>}
      {initiative.project_ids.length === 0 && initiative.hidden_project_count === 0 && (
        <p className="text-13 text-tertiary">{t("initiatives.projects.empty")}</p>
      )}
      <ul className="flex flex-col divide-y divide-subtle rounded-md border border-subtle">
        {initiative.project_ids.map((projectId) => {
          const project = getProjectById(projectId);
          return (
            <li key={projectId} className="flex items-center justify-between gap-2 px-3 py-2">
              <Link
                href={`/${workspaceSlug}/projects/${projectId}/issues`}
                className="flex min-w-0 items-center gap-2 text-13 text-primary hover:underline"
              >
                {project?.logo_props && <Logo logo={project.logo_props} size={16} />}
                <span className="shrink-0 text-tertiary">{project?.identifier}</span>
                <span className="truncate">{project?.name ?? t("initiatives.projects.unknown")}</span>
                {project?.archived_at && (
                  <span className="text-11 text-tertiary">{t("initiatives.projects.archived")}</span>
                )}
              </Link>
              {isInitiative && canLink(projectId) && (
                <IconButton
                  size="sm"
                  variant="ghost"
                  icon={<Icon icon={UnlinkOutline} />}
                  aria-label={t("initiatives.projects.remove", { name: project?.name ?? "" })}
                  onClick={() => void unlinkProject(workspaceSlug, initiative.id, projectId).catch(fail)}
                />
              )}
            </li>
          );
        })}
      </ul>
      <HiddenNote
        text={
          initiative.hidden_project_count > 0
            ? t("initiatives.progress.hidden_projects", { count: initiative.hidden_project_count })
            : undefined
        }
      />
    </section>
  );
});

function EpicRow(props: { workspaceSlug: string; epic: TInitiativeEpic; onRemove?: () => void }) {
  const { workspaceSlug, epic, onRemove } = props;
  const { t } = useTranslation();
  const percentage = getInitiativeProgressPercentage(epic.progress);
  const reference = `${epic.project_identifier}-${epic.sequence_id}`;
  return (
    <li className="flex items-center justify-between gap-3 px-3 py-2">
      <Link
        href={`/${workspaceSlug}/browse/${reference}/`}
        className="flex min-w-0 flex-1 items-center gap-2 text-13 text-primary hover:underline"
      >
        <EpicOutline className="size-4 shrink-0 text-tertiary" />
        <span className="shrink-0 text-tertiary">{reference}</span>
        <span className="truncate">{epic.name}</span>
      </Link>
      <div className="flex w-40 shrink-0 items-center gap-2">
        <div className="flex-1">
          <LinearProgress
            value={percentage}
            size="sm"
            variant={percentage === 100 ? "success" : "brand"}
            showValue={false}
            aria-label={t("initiatives.epics.progress_of", { name: epic.name })}
          />
        </div>
        <span className="w-16 text-right text-11 text-tertiary">
          {t("initiatives.progress.done_of_total", {
            done: epic.progress.completed + epic.progress.cancelled,
            total: epic.progress.total_issues,
          })}
        </span>
      </div>
      {onRemove && (
        <IconButton
          size="sm"
          variant="ghost"
          icon={<Icon icon={UnlinkOutline} />}
          aria-label={t("initiatives.epics.remove", { name: epic.name })}
          onClick={onRemove}
        />
      )}
    </li>
  );
}

/** Finds an Epic the person may link and links it */
const AddEpic = observer(function AddEpic(props: TProps) {
  const { workspaceSlug, initiative } = props;
  const { t } = useTranslation();
  const { searchEpics, linkEpics } = useInitiative();
  return (
    <Select<TInitiativeEpicOption>
      infinite
      getValues={async ({ search }) => {
        const results = await searchEpics(workspaceSlug, initiative.id, search ?? "");
        return { results, next_page_results: false, total_count: results.length };
      }}
      value={null}
      onChange={(epicId) => {
        if (!epicId) return;
        void linkEpics(workspaceSlug, initiative.id, [epicId]).catch((error: unknown) =>
          setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) })
        );
      }}
      getOptionValue={(option) => option.id}
      getOptionLabel={(option) => `${option.project_identifier}-${option.sequence_id} ${option.name}`}
      getOptionIcon={() => <EpicOutline className="size-3.5" />}
      searchPlaceholder={t("initiatives.epics.search")}
      emptyMessage={t("initiatives.epics.none_to_add")}
      pinSelected={false}
    >
      <Select.Trigger<TInitiativeEpicOption>
        variant="pill-md"
        prependIcon={() => <AddOutline className="size-3.5" />}
        label={() => t("initiatives.epics.add")}
      >
        {() => <span>{t("initiatives.epics.add")}</span>}
      </Select.Trigger>
    </Select>
  );
});

/** The linked Epics with the progress of their child work items; a goal shows those of its initiatives */
export const InitiativeEpics = observer(function InitiativeEpics(props: TProps) {
  const { workspaceSlug, initiative } = props;
  const { t } = useTranslation();
  const { epicsMap, fetchEpics, unlinkEpic } = useInitiative();
  const canLink = useLinkPermission(workspaceSlug);
  const isInitiative = initiative.kind === "initiative";
  // fetched again when the set of linked Epics changes
  useSWR(`INITIATIVE_EPICS_${initiative.id}_${initiative.epic_ids.join(",")}`, () =>
    fetchEpics(workspaceSlug, initiative.id)
  );
  const epics = epicsMap[initiative.id] ?? [];

  return (
    <section className="flex flex-col gap-2">
      <SectionHeading
        title={t("initiatives.epics.title")}
        count={initiative.epic_ids.length}
        action={isInitiative && <AddEpic workspaceSlug={workspaceSlug} initiative={initiative} />}
      />
      {!isInitiative && <p className="text-12 text-tertiary">{t("initiatives.epics.of_goal")}</p>}
      {initiative.epic_ids.length === 0 && initiative.hidden_epic_count === 0 && (
        <p className="text-13 text-tertiary">{t("initiatives.epics.empty")}</p>
      )}
      {epics.length > 0 && (
        <ul className="flex flex-col divide-y divide-subtle rounded-md border border-subtle">
          {epics.map((epic) => (
            <EpicRow
              key={epic.id}
              workspaceSlug={workspaceSlug}
              epic={epic}
              onRemove={
                isInitiative && canLink(epic.project_id)
                  ? () =>
                      void unlinkEpic(workspaceSlug, initiative.id, epic.id).catch((error: unknown) =>
                        setToast({
                          type: "error",
                          title: t("toast.error"),
                          message: getInitiativeErrorMessage(error, t),
                        })
                      )
                  : undefined
              }
            />
          ))}
        </ul>
      )}
      <HiddenNote
        text={
          initiative.hidden_epic_count > 0
            ? t("initiatives.progress.hidden_epics", { count: initiative.hidden_epic_count })
            : undefined
        }
      />
    </section>
  );
});
