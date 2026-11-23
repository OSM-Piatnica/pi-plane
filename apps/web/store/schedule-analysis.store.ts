/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, computed, makeObservable, observable, runInAction } from "mobx";
import type { TScheduleAnalysis, TScheduleAnalysisScope } from "@plane/types";
import { getValueFromLocalStorage, setValueIntoLocalStorage } from "@/hooks/use-local-storage";
import { IssueService } from "@/services/issue";

const CRITICAL_PATH_STORAGE_KEY = "timeline_critical_path";

/** What asks for the analysis: the timeline while its critical path is on, the list layouts while they show Float. */
export type TScheduleAnalysisDemand = "timeline" | "columns";

export interface IScheduleAnalysisStore {
  /** Whether the timeline highlights the critical path (remembered per browser). */
  isCriticalPathEnabled: boolean;
  /** Whether something asks for the analysis right now; it is only fetched then. */
  isActive: boolean;
  /** The last analysis the server answered, while something asks for it. */
  scheduleAnalysis: TScheduleAnalysis | undefined;
  isScheduleAnalysisLoading: boolean;
  /**
   * Counts the requests for an analysis: `scheduleAnalysisRequestId` is the last one asked for, `scheduleAnalysisResultId`
   * the one whose answer is in `scheduleAnalysis`. An answer to a request made before a change does not reflect it.
   */
  scheduleAnalysisRequestId: number;
  scheduleAnalysisResultId: number;
  toggleCriticalPath: () => void;
  /** Say that something does or no longer does need the analysis. The analysis is dropped when nothing does. */
  setDemand: (source: TScheduleAnalysisDemand, isDemanded: boolean) => void;
  /** Fetch the analysis of a project, or of one module or cycle of it. */
  fetchScheduleAnalysis: (workspaceSlug: string, projectId: string, scope?: TScheduleAnalysisScope) => Promise<void>;
  /** Fetch the analysis again for the project it was last fetched for; does nothing when there is none. */
  refreshScheduleAnalysis: (projectId: string) => Promise<void>;
}

type TScheduleAnalysisRequest = { workspaceSlug: string; projectId: string; scope: TScheduleAnalysisScope };

/**
 * The schedule analysis (critical path and float) of a project. The server computes it; this store holds the last
 * answer for whoever shows it: the timeline, the Float column of the list layouts and the work item sidebar.
 */
export class ScheduleAnalysisStore implements IScheduleAnalysisStore {
  isCriticalPathEnabled: boolean = getValueFromLocalStorage(CRITICAL_PATH_STORAGE_KEY, false) === true;
  scheduleAnalysis: TScheduleAnalysis | undefined = undefined;
  isScheduleAnalysisLoading = false;
  // what the analysis in the store was asked for, and a counter that lets a late answer of an older request be dropped
  scheduleAnalysisRequest: TScheduleAnalysisRequest | undefined = undefined;
  scheduleAnalysisRequestId = 0;
  scheduleAnalysisResultId = 0;
  demands = new Set<TScheduleAnalysisDemand>();

  issueService = new IssueService();

  constructor() {
    makeObservable(this, {
      isCriticalPathEnabled: observable.ref,
      scheduleAnalysis: observable.ref,
      isScheduleAnalysisLoading: observable.ref,
      scheduleAnalysisResultId: observable.ref,
      demands: observable.shallow,
      isActive: computed,
      toggleCriticalPath: action,
      setDemand: action,
    });
  }

  get isActive() {
    return this.demands.size > 0;
  }

  toggleCriticalPath = () => {
    this.isCriticalPathEnabled = !this.isCriticalPathEnabled;
    setValueIntoLocalStorage(CRITICAL_PATH_STORAGE_KEY, this.isCriticalPathEnabled);
  };

  setDemand = (source: TScheduleAnalysisDemand, isDemanded: boolean) => {
    if (isDemanded) this.demands.add(source);
    else this.demands.delete(source);
    if (this.demands.size === 0) {
      // drop the analysis and whatever answer is still on its way
      this.scheduleAnalysisRequestId += 1;
      this.scheduleAnalysisRequest = undefined;
      this.scheduleAnalysis = undefined;
      this.isScheduleAnalysisLoading = false;
    }
  };

  fetchScheduleAnalysis = async (workspaceSlug: string, projectId: string, scope: TScheduleAnalysisScope = {}) => {
    if (!this.isActive) return;
    const requestId = (this.scheduleAnalysisRequestId += 1);
    const isSameTarget =
      this.scheduleAnalysisRequest?.projectId === projectId &&
      this.scheduleAnalysisRequest.scope.module === scope.module &&
      this.scheduleAnalysisRequest.scope.cycle === scope.cycle;
    this.scheduleAnalysisRequest = { workspaceSlug, projectId, scope };
    runInAction(() => {
      this.isScheduleAnalysisLoading = true;
      // the analysis of another project, module or cycle says nothing about this one
      if (!isSameTarget) this.scheduleAnalysis = undefined;
    });
    try {
      const analysis = await this.issueService.getScheduleAnalysis(workspaceSlug, projectId, scope);
      if (requestId !== this.scheduleAnalysisRequestId) return;
      runInAction(() => {
        this.scheduleAnalysis = analysis;
        this.scheduleAnalysisResultId = requestId;
        this.isScheduleAnalysisLoading = false;
      });
    } catch (error) {
      if (requestId !== this.scheduleAnalysisRequestId) return;
      runInAction(() => {
        // a stale analysis would highlight the wrong bars
        this.scheduleAnalysis = undefined;
        this.isScheduleAnalysisLoading = false;
      });
      throw error;
    }
  };

  refreshScheduleAnalysis = async (projectId: string) => {
    const request = this.scheduleAnalysisRequest;
    if (!request || request.projectId !== projectId) return;
    await this.fetchScheduleAnalysis(request.workspaceSlug, request.projectId, request.scope);
  };
}
