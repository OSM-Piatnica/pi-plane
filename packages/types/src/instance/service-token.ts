/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * A bot token created in God Mode: a read-only API token of a workspace's service account, which is a member of
 * every project of the workspace (including projects created later).
 */
export type TInstanceServiceToken = {
  id: string;
  label: string;
  description: string;
  workspace: string | null;
  workspace_detail: { id: string; name: string; slug: string } | null;
  /** the last four characters, to tell tokens apart; the whole token is shown only when it is created */
  token_hint: string;
  is_active: boolean;
  is_expired: boolean;
  expired_at: string | null;
  last_used: string | null;
  created_at: string;
  created_by_detail: { id: string; display_name: string; email: string | null } | null;
  /** how many projects the service account belongs to, i.e. how many projects the token can read */
  project_count: number;
};

export type TInstanceServiceTokenCreate = {
  /** workspace id or slug */
  workspace: string;
  label: string;
  description?: string;
  /** ISO date or date-time; empty for a token that does not expire */
  expired_at?: string | null;
};

/** Returned once, right after the token is created */
export type TInstanceServiceTokenCreated = TInstanceServiceToken & { token: string };
