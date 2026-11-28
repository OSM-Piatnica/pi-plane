/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import type {
  TInitiative,
  TInitiativeEpic,
  TInitiativeEpicOption,
  TInitiativeFormData,
  TInitiativeHealth,
  TInitiativeUpdate,
} from "@plane/types";
import { buildInitiativeTree } from "@/helpers/initiatives";
import type { TInitiativeTreeNode } from "@/helpers/initiatives";
import { InitiativeService } from "@/services/initiative.service";

type TInitiativeApi = Pick<
  InitiativeService,
  | "list"
  | "retrieve"
  | "create"
  | "update"
  | "remove"
  | "linkProjects"
  | "unlinkProject"
  | "listEpics"
  | "searchEpics"
  | "linkEpics"
  | "unlinkEpic"
  | "listUpdates"
  | "createUpdate"
>;

export interface IInitiativeStore {
  /** The initiatives and goals of `workspaceSlug`, by id */
  initiativeMap: Record<string, TInitiative>;
  /** The workspace the map belongs to; another workspace starts from an empty map */
  workspaceSlug: string | undefined;
  /** True once the list of the workspace has been loaded */
  isListLoaded: boolean;
  epicsMap: Record<string, TInitiativeEpic[]>;
  updatesMap: Record<string, TInitiativeUpdate[]>;
  /** The goals with their initiatives, then the initiatives without a goal */
  tree: TInitiativeTreeNode[];
  goals: TInitiative[];
  getInitiativeById: (initiativeId: string | undefined) => TInitiative | undefined;
  fetchInitiatives: (workspaceSlug: string) => Promise<TInitiative[]>;
  fetchInitiative: (workspaceSlug: string, initiativeId: string) => Promise<TInitiative>;
  createInitiative: (workspaceSlug: string, data: TInitiativeFormData) => Promise<TInitiative>;
  /** Changes fields at once and puts them back when the request fails */
  updateInitiative: (workspaceSlug: string, initiativeId: string, data: TInitiativeFormData) => Promise<void>;
  deleteInitiative: (workspaceSlug: string, initiativeId: string) => Promise<void>;
  linkProjects: (workspaceSlug: string, initiativeId: string, projectIds: string[]) => Promise<void>;
  unlinkProject: (workspaceSlug: string, initiativeId: string, projectId: string) => Promise<void>;
  fetchEpics: (workspaceSlug: string, initiativeId: string) => Promise<TInitiativeEpic[]>;
  searchEpics: (workspaceSlug: string, initiativeId: string, search: string) => Promise<TInitiativeEpicOption[]>;
  linkEpics: (workspaceSlug: string, initiativeId: string, epicIds: string[]) => Promise<void>;
  unlinkEpic: (workspaceSlug: string, initiativeId: string, epicId: string) => Promise<void>;
  fetchUpdates: (workspaceSlug: string, initiativeId: string) => Promise<TInitiativeUpdate[]>;
  createUpdate: (
    workspaceSlug: string,
    initiativeId: string,
    data: { health: TInitiativeHealth; text: string }
  ) => Promise<TInitiativeUpdate>;
}

/** Initiatives and goals of the current workspace (`docs/initiatives.md`) */
export class InitiativeStore implements IInitiativeStore {
  initiativeMap: Record<string, TInitiative> = {};
  workspaceSlug: string | undefined = undefined;
  isListLoaded = false;
  epicsMap: Record<string, TInitiativeEpic[]> = {};
  updatesMap: Record<string, TInitiativeUpdate[]> = {};
  private service: TInitiativeApi;

  constructor(service: TInitiativeApi = new InitiativeService()) {
    makeObservable(this, {
      initiativeMap: observable,
      workspaceSlug: observable.ref,
      isListLoaded: observable.ref,
      epicsMap: observable,
      updatesMap: observable,
      tree: computed,
      goals: computed,
      fetchInitiatives: action,
      fetchInitiative: action,
      createInitiative: action,
      updateInitiative: action,
      deleteInitiative: action,
      linkProjects: action,
      unlinkProject: action,
      fetchEpics: action,
      linkEpics: action,
      unlinkEpic: action,
      fetchUpdates: action,
      createUpdate: action,
    });
    this.service = service;
  }

  get tree() {
    return buildInitiativeTree(Object.values(this.initiativeMap));
  }

  get goals() {
    return this.tree.flatMap((node) => (node.goal ? [node.goal] : []));
  }

  getInitiativeById = computedFn((initiativeId: string | undefined) =>
    initiativeId ? this.initiativeMap[initiativeId] : undefined
  );

  /** Starts over when another workspace is asked for, so no initiative of the previous one shows */
  private switchWorkspace = (workspaceSlug: string) => {
    if (this.workspaceSlug === workspaceSlug) return;
    runInAction(() => {
      this.workspaceSlug = workspaceSlug;
      this.initiativeMap = {};
      this.epicsMap = {};
      this.updatesMap = {};
      this.isListLoaded = false;
    });
  };

  private put = (workspaceSlug: string, initiative: TInitiative) => {
    if (this.workspaceSlug !== workspaceSlug) return;
    runInAction(() => {
      set(this.initiativeMap, [initiative.id], initiative);
    });
  };

  /**
   * After a link changes, the numbers of the initiative's goal change too; the goal is fetched
   * again when it is known. A failure there leaves the goal as it was, it is refreshed with the list.
   */
  private refreshGoalOf = async (workspaceSlug: string, initiative: TInitiative | undefined) => {
    if (!initiative?.parent) return;
    try {
      this.put(workspaceSlug, await this.service.retrieve(workspaceSlug, initiative.parent));
    } catch {
      // the goal keeps its previous numbers
    }
  };

  fetchInitiatives = async (workspaceSlug: string) => {
    this.switchWorkspace(workspaceSlug);
    const initiatives = await this.service.list(workspaceSlug);
    if (this.workspaceSlug !== workspaceSlug) return initiatives;
    runInAction(() => {
      this.initiativeMap = Object.fromEntries(initiatives.map((item) => [item.id, item]));
      this.isListLoaded = true;
    });
    return initiatives;
  };

  fetchInitiative = async (workspaceSlug: string, initiativeId: string) => {
    this.switchWorkspace(workspaceSlug);
    const initiative = await this.service.retrieve(workspaceSlug, initiativeId);
    this.put(workspaceSlug, initiative);
    return initiative;
  };

  createInitiative = async (workspaceSlug: string, data: TInitiativeFormData) => {
    this.switchWorkspace(workspaceSlug);
    const initiative = await this.service.create(workspaceSlug, data);
    this.put(workspaceSlug, initiative);
    await this.refreshGoalOf(workspaceSlug, initiative);
    return initiative;
  };

  updateInitiative = async (workspaceSlug: string, initiativeId: string, data: TInitiativeFormData) => {
    const before = this.initiativeMap[initiativeId];
    if (before) this.put(workspaceSlug, { ...before, ...data });
    try {
      const after = await this.service.update(workspaceSlug, initiativeId, data);
      this.put(workspaceSlug, after);
      // a new goal gains the numbers of the initiative, the old one loses them
      if ("parent" in data && before?.parent !== after.parent) {
        await this.refreshGoalOf(workspaceSlug, before);
        await this.refreshGoalOf(workspaceSlug, after);
      }
    } catch (error) {
      if (before) this.put(workspaceSlug, before);
      throw error;
    }
  };

  deleteInitiative = async (workspaceSlug: string, initiativeId: string) => {
    const before = this.initiativeMap[initiativeId];
    await this.service.remove(workspaceSlug, initiativeId);
    if (this.workspaceSlug !== workspaceSlug) return;
    runInAction(() => {
      delete this.initiativeMap[initiativeId];
      delete this.epicsMap[initiativeId];
      delete this.updatesMap[initiativeId];
      // the initiatives of a deleted goal stay, without a goal
      for (const item of Object.values(this.initiativeMap))
        if (item.parent === initiativeId) this.initiativeMap[item.id] = { ...item, parent: null };
    });
    await this.refreshGoalOf(workspaceSlug, before);
  };

  linkProjects = async (workspaceSlug: string, initiativeId: string, projectIds: string[]) => {
    const initiative = await this.service.linkProjects(workspaceSlug, initiativeId, projectIds);
    this.put(workspaceSlug, initiative);
    await this.refreshGoalOf(workspaceSlug, initiative);
  };

  unlinkProject = async (workspaceSlug: string, initiativeId: string, projectId: string) => {
    await this.service.unlinkProject(workspaceSlug, initiativeId, projectId);
    const initiative = await this.fetchInitiative(workspaceSlug, initiativeId);
    await this.refreshGoalOf(workspaceSlug, initiative);
  };

  fetchEpics = async (workspaceSlug: string, initiativeId: string) => {
    const epics = await this.service.listEpics(workspaceSlug, initiativeId);
    if (this.workspaceSlug === workspaceSlug)
      runInAction(() => {
        set(this.epicsMap, [initiativeId], epics);
      });
    return epics;
  };

  searchEpics = (workspaceSlug: string, initiativeId: string, search: string) =>
    this.service.searchEpics(workspaceSlug, initiativeId, search);

  linkEpics = async (workspaceSlug: string, initiativeId: string, epicIds: string[]) => {
    const initiative = await this.service.linkEpics(workspaceSlug, initiativeId, epicIds);
    this.put(workspaceSlug, initiative);
    await this.fetchEpics(workspaceSlug, initiativeId);
    await this.refreshGoalOf(workspaceSlug, initiative);
  };

  unlinkEpic = async (workspaceSlug: string, initiativeId: string, epicId: string) => {
    await this.service.unlinkEpic(workspaceSlug, initiativeId, epicId);
    if (this.workspaceSlug === workspaceSlug)
      runInAction(() => {
        const epics = this.epicsMap[initiativeId];
        if (epics)
          set(
            this.epicsMap,
            [initiativeId],
            epics.filter((epic) => epic.id !== epicId)
          );
      });
    const initiative = await this.fetchInitiative(workspaceSlug, initiativeId);
    await this.refreshGoalOf(workspaceSlug, initiative);
  };

  fetchUpdates = async (workspaceSlug: string, initiativeId: string) => {
    const updates = await this.service.listUpdates(workspaceSlug, initiativeId);
    if (this.workspaceSlug === workspaceSlug)
      runInAction(() => {
        set(this.updatesMap, [initiativeId], updates);
      });
    return updates;
  };

  createUpdate = async (
    workspaceSlug: string,
    initiativeId: string,
    data: { health: TInitiativeHealth; text: string }
  ) => {
    const update = await this.service.createUpdate(workspaceSlug, initiativeId, data);
    if (this.workspaceSlug === workspaceSlug)
      runInAction(() => {
        // newest first, as the API lists them
        set(this.updatesMap, [initiativeId], [update, ...(this.updatesMap[initiativeId] ?? [])]);
        const initiative = this.initiativeMap[initiativeId];
        // the health of the update becomes the health of the initiative
        if (initiative) this.initiativeMap[initiativeId] = { ...initiative, health: update.health };
      });
    return update;
  };
}
