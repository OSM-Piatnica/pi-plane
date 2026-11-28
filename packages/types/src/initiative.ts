/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IUserLite } from "./users";

/** A goal states an outcome; an initiative is a body of work toward it. See `docs/initiatives.md`. */
export type TInitiativeKind = "goal" | "initiative";

export type TInitiativeStatus = "planned" | "active" | "paused" | "completed" | "cancelled";

export type TInitiativeHealth = "on_track" | "at_risk" | "off_track";

/** Work items by state group, for the person who asks */
export type TInitiativeProgress = {
  total_issues: number;
  backlog: number;
  unstarted: number;
  started: number;
  completed: number;
  cancelled: number;
};

/** A goal or an initiative as the API returns it, with what the person may see of its links and progress */
export type TInitiative = {
  id: string;
  workspace: string;
  kind: TInitiativeKind;
  /** The goal of an initiative; always null for a goal */
  parent: string | null;
  name: string;
  description: string;
  description_html: string;
  lead: string | null;
  start_date: string | null;
  target_date: string | null;
  status: TInitiativeStatus;
  health: TInitiativeHealth | null;
  logo_props: Record<string, unknown>;
  color: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  /** The work items of the linked projects (of all its initiatives for a goal); Epics are not counted */
  progress: TInitiativeProgress;
  progress_is_partial: boolean;
  hidden_project_count: number;
  project_ids: string[];
  epic_ids: string[];
  hidden_epic_count: number;
  /** The initiatives of a goal; empty for an initiative */
  initiative_ids: string[];
  /** The child work items of the linked Epics the person may see, apart from `progress` */
  epic_progress: TInitiativeProgress;
  epic_progress_is_partial: boolean;
};

/** What the create and edit forms send */
export type TInitiativeFormData = Partial<
  Pick<
    TInitiative,
    | "kind"
    | "parent"
    | "name"
    | "description_html"
    | "lead"
    | "start_date"
    | "target_date"
    | "status"
    | "logo_props"
    | "color"
  >
>;

/** A status note: how it is going, in words and as a health */
export type TInitiativeUpdate = {
  id: string;
  initiative: string;
  author: string;
  author_detail?: IUserLite;
  health: TInitiativeHealth;
  text: string;
  created_at: string;
};

/** An Epic that can be linked to an initiative (`GET .../epics/search/`) */
export type TInitiativeEpicOption = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  project_identifier: string;
};

/** A linked Epic the person may see, with the progress of its child work items (`GET .../epics/`) */
export type TInitiativeEpic = TInitiativeEpicOption & {
  state_id: string | null;
  state_group: string | null;
  target_date: string | null;
  progress: TInitiativeProgress;
  progress_is_partial: boolean;
};
