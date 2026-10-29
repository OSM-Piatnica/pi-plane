/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { IUserLite } from "../users";
import type {
  TInstanceAIConfigurationKeys,
  TInstanceEmailConfigurationKeys,
  TInstanceImageConfigurationKeys,
  TInstanceAuthenticationKeys,
  TInstanceUploadConfigurationKeys,
  TInstanceWorkspaceConfigurationKeys,
  TCoreLoginMediums,
  TOidcProviderOption,
} from "./";
import type { TExtendedLoginMediums } from "./auth-ee";

export interface IInstanceInfo {
  instance: IInstance;
  config: IInstanceConfig;
}

export interface IInstance {
  id: string;
  created_at: string;
  updated_at: string;
  instance_name: string | undefined;
  whitelist_emails: string | undefined;
  instance_id: string | undefined;
  license_key: string | undefined;
  current_version: string | undefined;
  latest_version: string | undefined;
  last_checked_at: string | undefined;
  namespace: string | undefined;
  is_telemetry_enabled: boolean;
  is_support_required: boolean;
  is_activated: boolean;
  is_setup_done: boolean;
  is_signup_screen_visited: boolean;
  user_count: number | undefined;
  is_verified: boolean;
  created_by: string | undefined;
  updated_by: string | undefined;
  workspaces_exist: boolean;
}

export interface IInstanceConfig {
  enable_signup: boolean;
  is_workspace_creation_disabled: boolean;
  is_github_enabled: boolean;
  is_gitlab_enabled: boolean;
  is_gitea_enabled: boolean;
  oidc_providers?: TOidcProviderOption[];
  is_magic_login_enabled: boolean;
  is_email_password_enabled: boolean;
  /** Workspace UUID used to resolve compact `/i/PROJECT-123` work item links; empty when short links are off. */
  default_workspace_id?: string;
  /** Projects can be shared on the web: Space is part of this installation and switched on. */
  is_space_enabled?: boolean;
  /** Space is part of this installation; when it is not, the administrator cannot switch it on. */
  is_space_deployed?: boolean;
  github_app_name: string | undefined;
  slack_client_id: string | undefined;
  has_unsplash_configured: boolean;
  has_llm_configured: boolean;
  /** The largest upload in bytes: the administrator's setting, else the deployment default. */
  file_size_limit: number | undefined;
  /** The most the administrator can set it to, in bytes. */
  file_size_limit_max?: number;
  /** The largest spreadsheet for a work item import, in bytes. */
  import_file_size_limit?: number;
  /** The most work items one import may hold. */
  import_max_work_items?: number;
  /** The most the administrator can set `import_max_work_items` to. */
  import_max_work_items_max?: number;
  is_smtp_configured: boolean;
  app_base_url: string | undefined;
  space_base_url: string | undefined;
  admin_base_url: string | undefined;
  is_self_managed: boolean;
  instance_changelog_url?: string;
}

export interface IInstanceAdmin {
  created_at: string;
  created_by: string;
  id: string;
  instance: string;
  role: string;
  updated_at: string;
  updated_by: string;
  user: string;
  user_detail: IUserLite;
}

export type TInstanceConfigurationKeys =
  | TInstanceAIConfigurationKeys
  | TInstanceEmailConfigurationKeys
  | TInstanceImageConfigurationKeys
  | TInstanceAuthenticationKeys
  | TInstanceUploadConfigurationKeys
  | TInstanceWorkspaceConfigurationKeys;

export interface IInstanceConfiguration {
  id: string;
  created_at: string;
  updated_at: string;
  key: TInstanceConfigurationKeys;
  value: string;
  created_by: string | null;
  updated_by: string | null;
}

export type IFormattedInstanceConfiguration = {
  [key in TInstanceConfigurationKeys]: string;
};

export type TLoginMediums = TCoreLoginMediums | TExtendedLoginMediums;
