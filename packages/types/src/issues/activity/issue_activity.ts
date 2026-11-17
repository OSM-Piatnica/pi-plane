/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// local imports
import type { EInboxIssueSource } from "../../inbox";
import type {
  TIssueActivityWorkspaceDetail,
  TIssueActivityProjectDetail,
  TIssueActivityIssueDetail,
  TIssueActivityUserDetail,
} from "./base";

/** The work item whose date change moved another one along (a shift of dependents). */
export type TIssueActivityShiftCause = {
  id: string;
  project_id: string;
  sequence_id: number;
  project_identifier: string;
};

export type TIssueActivity = {
  id: string;
  workspace: string;
  workspace_detail: TIssueActivityWorkspaceDetail;
  project: string;
  project_detail: TIssueActivityProjectDetail;
  issue: string;
  issue_detail: TIssueActivityIssueDetail;
  actor: string;
  actor_detail: TIssueActivityUserDetail;
  created_at: string;
  updated_at: string;
  created_by: string | undefined;
  updated_by: string | undefined;
  attachments: any[];

  verb: string;
  field: string | undefined;
  old_value: string | undefined;
  new_value: string | undefined;
  comment: string | undefined;
  old_identifier: string | undefined;
  new_identifier: string | undefined;
  epoch: number;
  issue_comment: string | null;
  /** Set on a start or finish date entry written when the work item was moved along with another one. */
  shift_cause?: TIssueActivityShiftCause | null;
  source_data: {
    source: EInboxIssueSource;
    source_email?: string;
    extra: {
      username?: string;
    };
  };
};

export type TIssueActivityMap = {
  [issue_id: string]: TIssueActivity;
};

export type TIssueActivityIdMap = {
  [issue_id: string]: string[];
};
