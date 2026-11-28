/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Check } from "lucide-react";
// plane imports
import {
  Menu,
  MenuContent,
  MenuGroup,
  MenuItem,
  MenuLabel,
  MenuSeparator,
  MenuSubmenu,
  MenuSubmenuContent,
  MenuSubmenuTrigger,
  MenuTrigger,
} from "@makeplane/propel/components/menu";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { EIssuesStoreType, TProjectBaseline } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// helpers
import {
  formatSignedDays,
  getBaselineKey,
  getComparedBaseline,
  getDefaultBaselineName,
  getVarianceText,
} from "@/helpers/baseline.helper";
import { getScheduleAnalysisScope } from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssuesTimeLineChart } from "@/hooks/use-timeline-chart";
// local imports
import { BaselineDeleteDialog, BaselineNameDialog } from "./baseline-dialogs";

type TLoaderProps = {
  issueIds: string[];
  storeType: EIssuesStoreType;
};

/**
 * Asks the server for the comparison with the baseline while it is shown, and again when a date of a loaded work item
 * changes or another baseline is picked, saved, activated or deleted. It renders nothing; being a component of its
 * own, it is the only one that re-renders when a date changes, not the whole layout.
 */
export const GanttBaselineLoader = observer(function GanttBaselineLoader(props: TLoaderProps) {
  const { issueIds, storeType } = props;
  const { t } = useTranslation();
  const { workspaceSlug, projectId, moduleId, cycleId } = useParams();
  const {
    baseline: { isBaselineShown, revision, fetchVariance },
  } = useIssuesTimeLineChart();
  const {
    issue: { getIssueById },
  } = useIssueDetail();

  // a module or a cycle timeline compares the work items of that module or cycle, like the critical path
  const { module: scopeModule, cycle: scopeCycle } = getScheduleAnalysisScope(storeType, {
    moduleId: moduleId?.toString(),
    cycleId: cycleId?.toString(),
  });
  const isAsking = isBaselineShown && !!workspaceSlug && !!projectId;
  const datesKey = isAsking ? getBaselineKey(issueIds, getIssueById) : "";

  useEffect(() => {
    if (!isAsking || !workspaceSlug || !projectId) return;
    const timeout = setTimeout(() => {
      fetchVariance(workspaceSlug.toString(), projectId.toString(), { module: scopeModule, cycle: scopeCycle }).catch(
        () => {
          setToast({ type: "error", title: t("toast.error"), message: t("baseline.load_error") });
        }
      );
    }, 300);
    return () => clearTimeout(timeout);
    // datesKey stands for the dates the comparison depends on; t only matters when the request fails
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [datesKey, revision, isAsking, workspaceSlug, projectId, scopeModule, scopeCycle, fetchVariance]);

  return null;
});

type Props = {
  workspaceSlug: string;
  projectId: string;
  /** Whether the person may save, rename, delete and activate baselines (project admins and members). */
  canManage: boolean;
};

type TDialog = { type: "save" } | { type: "rename" | "delete"; baseline: TProjectBaseline };

/**
 * The baseline of the timeline: save the current plan, pick which saved plan to compare with, and switch the grey
 * trace of that plan on or off. The baselines are listed when the menu opens, the comparison only while it is shown.
 */
export const GanttBaselineControl = observer(function GanttBaselineControl(props: Props) {
  const { workspaceSlug, projectId, canManage } = props;
  const { t } = useTranslation();
  const { baseline: store } = useIssuesTimeLineChart();
  const [dialog, setDialog] = useState<TDialog | undefined>();

  const showError = (message: string) => setToast({ type: "error", title: t("toast.error"), message });

  const loadBaselines = () => {
    store.fetchBaselines(workspaceSlug, projectId).catch(() => showError(t("baseline.load_error")));
  };

  const compared = getComparedBaseline(store.baselines, store.selectedBaselineId);
  const endVariance = store.isBaselineShown ? (store.variance?.summary.end_variance ?? null) : null;

  const compareWith = (baseline: TProjectBaseline) => {
    store.selectBaseline(baseline.is_active ? undefined : baseline.id);
    if (!store.isBaselineShown) store.toggleBaseline();
  };

  const save = async (name: string) => {
    try {
      await store.saveBaseline(workspaceSlug, projectId, name);
      setToast({ type: "success", title: t("toast.success"), message: t("baseline.saved") });
    } catch (error) {
      const details = error as { code?: string; max_baselines?: number } | undefined;
      showError(
        details?.code === "baseline_limit_reached"
          ? t("baseline.limit_reached", { count: details.max_baselines ?? store.maxBaselines ?? 0 })
          : t("baseline.save_error")
      );
      throw error;
    }
  };

  const update = async (baseline: TProjectBaseline, data: { name?: string; is_active?: boolean }) => {
    try {
      await store.updateBaseline(workspaceSlug, projectId, baseline.id, data);
    } catch (error) {
      showError(t("baseline.update_error"));
      throw error;
    }
  };

  const remove = async (baseline: TProjectBaseline) => {
    try {
      await store.deleteBaseline(workspaceSlug, projectId, baseline.id);
      setToast({ type: "success", title: t("toast.success"), message: t("baseline.deleted") });
    } catch (error) {
      showError(t("baseline.delete_error"));
      throw error;
    }
  };

  const getBaselineLabel = (baseline: TProjectBaseline) =>
    baseline.is_active ? `${baseline.name} · ${t("baseline.active")}` : baseline.name;

  const titleLines = [t("baseline.tooltip")];
  if (endVariance !== null)
    titleLines.push(
      t("baseline.end_variance_tooltip", {
        variance: getVarianceText(endVariance, t),
      })
    );

  return (
    <>
      <Menu
        onOpenChange={(open) => {
          if (open) loadBaselines();
        }}
      >
        <MenuTrigger
          render={
            <button
              type="button"
              className={cn(
                "flex items-center gap-1 rounded-md bg-layer-transparent p-1 px-2 text-11 hover:bg-layer-transparent-hover",
                { "bg-layer-transparent-selected": store.isBaselineShown }
              )}
              title={titleLines.join(" ")}
              data-testid="gantt-baseline-control"
            />
          }
        >
          {t("baseline.label")}
          {endVariance !== null && endVariance !== 0 && (
            <span
              className={cn("font-medium", endVariance > 0 ? "text-danger-primary" : "text-success-primary")}
              data-testid="gantt-baseline-end-variance"
            >
              {t("baseline.variance_days", { days: formatSignedDays(endVariance) })}
            </span>
          )}
        </MenuTrigger>
        <MenuContent side="bottom" align="end">
          <MenuItem label={t("baseline.show")} selected={store.isBaselineShown} onClick={store.toggleBaseline} />
          {canManage && <MenuItem label={t("baseline.save")} onClick={() => setDialog({ type: "save" })} />}
          <MenuSeparator />
          <MenuGroup>
            <MenuLabel>{t("baseline.saved_baselines")}</MenuLabel>
            {store.baselines?.length === 0 && <MenuItem label={t("baseline.none")} disabled />}
            {store.baselines?.map((baseline) =>
              canManage ? (
                <MenuSubmenu key={baseline.id}>
                  <MenuSubmenuTrigger
                    label={getBaselineLabel(baseline)}
                    trailing={compared?.id === baseline.id ? <Check className="size-3.5 shrink-0" /> : undefined}
                  />
                  <MenuSubmenuContent sizing="auto">
                    <MenuItem
                      label={t("baseline.compare")}
                      secondaryText={renderFormattedDate(baseline.created_at) ?? undefined}
                      selected={compared?.id === baseline.id}
                      onClick={() => compareWith(baseline)}
                    />
                    {!baseline.is_active && (
                      <MenuItem
                        label={t("baseline.set_active")}
                        onClick={() => {
                          update(baseline, { is_active: true }).catch(() => undefined);
                        }}
                      />
                    )}
                    <MenuItem label={t("baseline.rename")} onClick={() => setDialog({ type: "rename", baseline })} />
                    <MenuItem
                      variant="danger"
                      label={t("delete")}
                      onClick={() => setDialog({ type: "delete", baseline })}
                    />
                  </MenuSubmenuContent>
                </MenuSubmenu>
              ) : (
                <MenuItem
                  key={baseline.id}
                  label={getBaselineLabel(baseline)}
                  secondaryText={renderFormattedDate(baseline.created_at) ?? undefined}
                  selected={compared?.id === baseline.id}
                  onClick={() => compareWith(baseline)}
                />
              )
            )}
          </MenuGroup>
        </MenuContent>
      </Menu>
      {dialog?.type === "save" && (
        <BaselineNameDialog
          title={t("baseline.save")}
          description={t("baseline.save_description")}
          initialName={getDefaultBaselineName(t("baseline.label"), renderFormattedDate(new Date()) ?? "")}
          onClose={() => setDialog(undefined)}
          onSubmit={save}
        />
      )}
      {dialog?.type === "rename" && (
        <BaselineNameDialog
          title={t("baseline.rename_title")}
          initialName={dialog.baseline.name}
          onClose={() => setDialog(undefined)}
          onSubmit={(name) => update(dialog.baseline, { name })}
        />
      )}
      {dialog?.type === "delete" && (
        <BaselineDeleteDialog
          name={dialog.baseline.name}
          onClose={() => setDialog(undefined)}
          onConfirm={() => remove(dialog.baseline)}
        />
      )}
    </>
  );
});

type TToolsProps = TLoaderProps & Pick<Props, "canManage">;

/** The baseline loader and menu for the timeline header of a project's work items; nothing outside a project. */
export const GanttBaselineTools = observer(function GanttBaselineTools(props: TToolsProps) {
  const { issueIds, storeType, canManage } = props;
  const { workspaceSlug, projectId } = useParams();
  if (!workspaceSlug || !projectId) return null;
  return (
    <>
      <GanttBaselineLoader issueIds={issueIds} storeType={storeType} />
      <GanttBaselineControl
        workspaceSlug={workspaceSlug.toString()}
        projectId={projectId.toString()}
        canManage={canManage}
      />
    </>
  );
});
