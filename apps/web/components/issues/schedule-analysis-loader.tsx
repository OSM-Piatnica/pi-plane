/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { EIssuesStoreType } from "@plane/types";
// helpers
import { getScheduleAnalysisKey, getScheduleAnalysisScope } from "@/helpers/schedule-analysis.helper";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useScheduleAnalysis } from "@/hooks/use-schedule-analysis";
import type { TScheduleAnalysisDemand } from "@/store/schedule-analysis.store";

type Props = {
  issueIds: string[];
  storeType: EIssuesStoreType;
  /** What asks for the analysis; the store drops it once nothing does. */
  source: TScheduleAnalysisDemand;
  isEnabled: boolean;
};

/**
 * Asks the server for the schedule analysis while `isEnabled`, and again when a date, a state, a relation or a lag
 * of a loaded work item changes: the key stands for all of those. It renders nothing. Being a component of its own, it
 * is the only one that re-renders when one of those changes, not the whole layout.
 */
export const ScheduleAnalysisLoader = observer(function ScheduleAnalysisLoader(props: Props) {
  const { issueIds, storeType, source, isEnabled } = props;
  const { t } = useTranslation();
  const { workspaceSlug, projectId, moduleId, cycleId } = useParams();
  const { setDemand, fetchScheduleAnalysis } = useScheduleAnalysis();
  const {
    issue: { getIssueById },
    relation: { relationMap, getRelationLag },
  } = useIssueDetail();

  const { module: scopeModule, cycle: scopeCycle } = getScheduleAnalysisScope(storeType, {
    moduleId: moduleId?.toString(),
    cycleId: cycleId?.toString(),
  });
  // a layout without a project (a workspace view) has no single schedule to analyse
  const isAsking = isEnabled && !!workspaceSlug && !!projectId;
  const analysisKey = isAsking ? getScheduleAnalysisKey(issueIds, getIssueById, relationMap, getRelationLag) : "";

  useEffect(() => {
    if (!isAsking) return;
    setDemand(source, true);
    return () => setDemand(source, false);
  }, [isAsking, source, setDemand]);

  useEffect(() => {
    if (!isAsking || !workspaceSlug || !projectId) return;
    const timeout = setTimeout(() => {
      fetchScheduleAnalysis(workspaceSlug.toString(), projectId.toString(), {
        module: scopeModule,
        cycle: scopeCycle,
      }).catch(() => {
        setToast({ type: "error", title: t("toast.error"), message: t("schedule_analysis.load_error") });
      });
    }, 300);
    return () => clearTimeout(timeout);
    // analysisKey stands for what the analysis depends on; t only matters when the request fails
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisKey, isAsking, workspaceSlug, projectId, scopeModule, scopeCycle, fetchScheduleAnalysis]);

  return null;
});
