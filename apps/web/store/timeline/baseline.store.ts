/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import type { TBaselineVariance, TProjectBaseline, TScheduleAnalysisScope } from "@plane/types";
import { getValueFromLocalStorage, setValueIntoLocalStorage } from "@/hooks/use-local-storage";
import { ProjectBaselineService } from "@/services/project/project-baseline.service";
import type { TProjectBaselineUpdate } from "@/services/project/project-baseline.service";

const SHOW_BASELINE_STORAGE_KEY = "timeline_show_baseline";

/** The same baseline, no longer the active one; a copy, as the list is replaced rather than changed in place. */
const withoutActive = (baseline: TProjectBaseline): TProjectBaseline =>
  baseline.is_active ? Object.assign({}, baseline, { is_active: false }) : baseline;

type TVarianceRequest = { workspaceSlug: string; projectId: string; scope: TScheduleAnalysisScope };

export interface IBaselineStore {
  /** Whether the timeline draws the trace of a saved plan. The comparison is only fetched while this is on. */
  isBaselineShown: boolean;
  /** The baselines of the project they were last listed for, newest first; undefined until listed. */
  baselines: TProjectBaseline[] | undefined;
  maxBaselines: number | undefined;
  /** A baseline picked to compare with instead of the active one; not remembered between visits. */
  selectedBaselineId: string | undefined;
  /** The last comparison the server answered, while the baseline is shown. */
  variance: TBaselineVariance | undefined;
  isVarianceLoading: boolean;
  /** Changes whenever the baselines change in a way that makes the comparison stale. */
  revision: number;
  toggleBaseline: () => void;
  selectBaseline: (baselineId: string | undefined) => void;
  fetchBaselines: (workspaceSlug: string, projectId: string) => Promise<void>;
  /** Fetch the comparison with the picked or active baseline, for a project or one module or cycle of it. */
  fetchVariance: (workspaceSlug: string, projectId: string, scope?: TScheduleAnalysisScope) => Promise<void>;
  /** Save the current plan as a new baseline, which becomes the active one, and show it. */
  saveBaseline: (workspaceSlug: string, projectId: string, name: string) => Promise<TProjectBaseline>;
  /** Rename a baseline or make it the active one. */
  updateBaseline: (
    workspaceSlug: string,
    projectId: string,
    baselineId: string,
    data: TProjectBaselineUpdate
  ) => Promise<TProjectBaseline>;
  deleteBaseline: (workspaceSlug: string, projectId: string, baselineId: string) => Promise<void>;
}

export class BaselineStore implements IBaselineStore {
  isBaselineShown: boolean = getValueFromLocalStorage(SHOW_BASELINE_STORAGE_KEY, false) === true;
  baselines: TProjectBaseline[] | undefined = undefined;
  maxBaselines: number | undefined = undefined;
  selectedBaselineId: string | undefined = undefined;
  variance: TBaselineVariance | undefined = undefined;
  isVarianceLoading = false;
  revision = 0;
  // the project the baselines belong to, what the comparison was asked for, and a counter that lets a late answer of
  // an older request be dropped
  baselinesProjectId: string | undefined = undefined;
  varianceRequest: TVarianceRequest | undefined = undefined;
  varianceRequestId = 0;

  baselineService = new ProjectBaselineService();

  constructor() {
    makeObservable(this, {
      isBaselineShown: observable.ref,
      baselines: observable.ref,
      maxBaselines: observable.ref,
      selectedBaselineId: observable.ref,
      variance: observable.ref,
      isVarianceLoading: observable.ref,
      revision: observable.ref,
      toggleBaseline: action,
      selectBaseline: action,
    });
  }

  private setShown(isShown: boolean) {
    this.isBaselineShown = isShown;
    setValueIntoLocalStorage(SHOW_BASELINE_STORAGE_KEY, isShown);
    if (!isShown) {
      // drop the comparison and whatever answer is still on its way
      this.varianceRequestId += 1;
      this.varianceRequest = undefined;
      this.variance = undefined;
      this.isVarianceLoading = false;
    }
  }

  toggleBaseline = () => {
    this.setShown(!this.isBaselineShown);
  };

  selectBaseline = (baselineId: string | undefined) => {
    if (this.selectedBaselineId === baselineId) return;
    this.selectedBaselineId = baselineId;
    this.revision += 1;
  };

  /** The baselines of another project say nothing about this one. */
  private useProject(projectId: string) {
    if (this.baselinesProjectId === projectId) return;
    this.baselinesProjectId = projectId;
    this.baselines = undefined;
    this.selectedBaselineId = undefined;
  }

  fetchBaselines = async (workspaceSlug: string, projectId: string) => {
    runInAction(() => this.useProject(projectId));
    const response = await this.baselineService.list(workspaceSlug, projectId);
    if (this.baselinesProjectId !== projectId) return;
    runInAction(() => {
      this.baselines = response.baselines;
      this.maxBaselines = response.max_baselines;
      // a picked baseline that somebody else deleted meanwhile
      if (this.selectedBaselineId && !response.baselines.some((baseline) => baseline.id === this.selectedBaselineId))
        this.selectedBaselineId = undefined;
    });
  };

  fetchVariance = async (workspaceSlug: string, projectId: string, scope: TScheduleAnalysisScope = {}) => {
    if (!this.isBaselineShown) return;
    const requestId = (this.varianceRequestId += 1);
    const isSameTarget =
      this.varianceRequest?.projectId === projectId &&
      this.varianceRequest.scope.module === scope.module &&
      this.varianceRequest.scope.cycle === scope.cycle;
    this.varianceRequest = { workspaceSlug, projectId, scope };
    runInAction(() => {
      this.useProject(projectId);
      this.isVarianceLoading = true;
      // the comparison of another project, module or cycle says nothing about this one
      if (!isSameTarget) this.variance = undefined;
    });
    try {
      const variance = await this.baselineService.getVariance(workspaceSlug, projectId, {
        ...scope,
        ...(this.selectedBaselineId ? { baseline: this.selectedBaselineId } : {}),
      });
      if (requestId !== this.varianceRequestId) return;
      runInAction(() => {
        this.variance = variance;
        this.isVarianceLoading = false;
      });
    } catch (error) {
      if (requestId !== this.varianceRequestId) return;
      runInAction(() => {
        // a stale comparison would draw the trace of a plan in the wrong place
        this.variance = undefined;
        this.isVarianceLoading = false;
      });
      throw error;
    }
  };

  saveBaseline = async (workspaceSlug: string, projectId: string, name: string) => {
    const baseline = await this.baselineService.create(workspaceSlug, projectId, { name });
    runInAction(() => {
      this.useProject(projectId);
      // the new baseline is the active one, so the others no longer are
      this.baselines = [baseline, ...(this.baselines ?? []).map(withoutActive)];
      this.selectedBaselineId = undefined;
      this.revision += 1;
      if (!this.isBaselineShown) this.setShown(true);
    });
    return baseline;
  };

  updateBaseline = async (
    workspaceSlug: string,
    projectId: string,
    baselineId: string,
    data: TProjectBaselineUpdate
  ) => {
    const updated = await this.baselineService.update(workspaceSlug, projectId, baselineId, data);
    if (this.baselinesProjectId !== projectId) return updated;
    runInAction(() => {
      this.baselines = this.baselines?.map((baseline) => {
        if (baseline.id === updated.id) return updated;
        return updated.is_active ? withoutActive(baseline) : baseline;
      });
      if (data.is_active !== undefined) {
        // making a baseline the active one is also a wish to see it
        if (data.is_active) this.selectedBaselineId = undefined;
        this.revision += 1;
      } else if (this.variance?.baseline?.id === updated.id) {
        this.variance = { ...this.variance, baseline: updated };
      }
    });
    return updated;
  };

  deleteBaseline = async (workspaceSlug: string, projectId: string, baselineId: string) => {
    await this.baselineService.remove(workspaceSlug, projectId, baselineId);
    if (this.baselinesProjectId !== projectId) return;
    runInAction(() => {
      this.baselines = this.baselines?.filter((baseline) => baseline.id !== baselineId);
      if (this.selectedBaselineId === baselineId) this.selectedBaselineId = undefined;
      this.revision += 1;
    });
  };
}
