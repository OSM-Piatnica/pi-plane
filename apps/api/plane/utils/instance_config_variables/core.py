# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Python imports
import os

authentication_config_variables = [
    {
        "key": "ENABLE_SIGNUP",
        "value": os.environ.get("ENABLE_SIGNUP", "1"),
        "category": "AUTHENTICATION",
        "is_encrypted": False,
    },
    {
        "key": "ENABLE_EMAIL_PASSWORD",
        "value": os.environ.get("ENABLE_EMAIL_PASSWORD", "1"),
        "category": "AUTHENTICATION",
        "is_encrypted": False,
    },
    {
        "key": "ENABLE_MAGIC_LINK_LOGIN",
        "value": os.environ.get("ENABLE_MAGIC_LINK_LOGIN", "0"),
        "category": "AUTHENTICATION",
        "is_encrypted": False,
    },
]

workspace_management_config_variables = [
    {
        "key": "DISABLE_WORKSPACE_CREATION",
        "value": os.environ.get("DISABLE_WORKSPACE_CREATION", "0"),
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Largest upload in bytes, set in the admin app. Empty means the FILE_SIZE_LIMIT environment default.
        "key": "FILE_SIZE_LIMIT",
        "value": "",
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Largest spreadsheet for a work item import, in bytes, set in the admin app. Empty means the default.
        "key": "IMPORT_FILE_SIZE_LIMIT",
        "value": "",
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Most work items in one import, set in the admin app. Empty means the default.
        "key": "IMPORT_MAX_WORK_ITEMS",
        "value": "",
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Most messages one person may send to the admins of a workspace within an hour, set in the admin app. Empty
        # means the default of the deployment (ADMIN_MESSAGE_LIMIT_PER_HOUR, else 5).
        "key": "ADMIN_MESSAGE_LIMIT",
        "value": "",
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Whether projects can be shared on the web through Space; "0" turns it off. Only matters while Space is part
        # of the deployment (ENABLE_SPACE).
        "key": "IS_SPACE_ENABLED",
        "value": os.environ.get("IS_SPACE_ENABLED", "1"),
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
    {
        # Workspace UUID that gets compact `/i/PROJ-123` work item links; empty turns them off.
        "key": "INSTANCE_DEFAULT_WORKSPACE_ID",
        "value": os.environ.get("INSTANCE_DEFAULT_WORKSPACE_ID", ""),
        "category": "WORKSPACE_MANAGEMENT",
        "is_encrypted": False,
    },
]

github_config_variables = [
    {
        "key": "IS_GITHUB_ENABLED",
        "value": os.environ.get("IS_GITHUB_ENABLED", "0"),
        "category": "GITHUB",
        "is_encrypted": False,
    },
    {
        "key": "GITHUB_CLIENT_ID",
        "value": os.environ.get("GITHUB_CLIENT_ID"),
        "category": "GITHUB",
        "is_encrypted": False,
    },
    {
        "key": "GITHUB_CLIENT_SECRET",
        "value": os.environ.get("GITHUB_CLIENT_SECRET"),
        "category": "GITHUB",
        "is_encrypted": True,
    },
    {
        "key": "GITHUB_ORGANIZATION_ID",
        "value": os.environ.get("GITHUB_ORGANIZATION_ID"),
        "category": "GITHUB",
        "is_encrypted": False,
    },
    {
        "key": "ENABLE_GITHUB_SYNC",
        "value": os.environ.get("ENABLE_GITHUB_SYNC", "0"),
        "category": "GITHUB",
        "is_encrypted": False,
    },
]


gitlab_config_variables = [
    {
        "key": "IS_GITLAB_ENABLED",
        "value": os.environ.get("IS_GITLAB_ENABLED", "0"),
        "category": "GITLAB",
        "is_encrypted": False,
    },
    {
        "key": "GITLAB_HOST",
        "value": os.environ.get("GITLAB_HOST"),
        "category": "GITLAB",
        "is_encrypted": False,
    },
    {
        "key": "GITLAB_CLIENT_ID",
        "value": os.environ.get("GITLAB_CLIENT_ID"),
        "category": "GITLAB",
        "is_encrypted": False,
    },
    {
        "key": "GITLAB_CLIENT_SECRET",
        "value": os.environ.get("GITLAB_CLIENT_SECRET"),
        "category": "GITLAB",
        "is_encrypted": True,
    },
    {
        "key": "ENABLE_GITLAB_SYNC",
        "value": os.environ.get("ENABLE_GITLAB_SYNC", "0"),
        "category": "GITLAB",
        "is_encrypted": False,
    },
]

gitea_config_variables = [
    {
        "key": "IS_GITEA_ENABLED",
        "value": os.environ.get("IS_GITEA_ENABLED", "0"),
        "category": "GITEA",
        "is_encrypted": False,
    },
    {
        "key": "GITEA_HOST",
        "value": os.environ.get("GITEA_HOST"),
        "category": "GITEA",
        "is_encrypted": False,
    },
    {
        "key": "GITEA_CLIENT_ID",
        "value": os.environ.get("GITEA_CLIENT_ID"),
        "category": "GITEA",
        "is_encrypted": False,
    },
    {
        "key": "GITEA_CLIENT_SECRET",
        "value": os.environ.get("GITEA_CLIENT_SECRET"),
        "category": "GITEA",
        "is_encrypted": True,
    },
    {
        "key": "ENABLE_GITEA_SYNC",
        "value": os.environ.get("ENABLE_GITEA_SYNC", "0"),
        "category": "GITEA",
        "is_encrypted": False,
    },
]

smtp_config_variables = [
    {
        "key": "ENABLE_SMTP",
        "value": os.environ.get("ENABLE_SMTP", "0"),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_HOST",
        "value": os.environ.get("EMAIL_HOST", ""),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_HOST_USER",
        "value": os.environ.get("EMAIL_HOST_USER", ""),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_HOST_PASSWORD",
        "value": os.environ.get("EMAIL_HOST_PASSWORD", ""),
        "category": "SMTP",
        "is_encrypted": True,
    },
    {
        "key": "EMAIL_PORT",
        "value": os.environ.get("EMAIL_PORT", "587"),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_FROM",
        "value": os.environ.get("EMAIL_FROM", ""),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_USE_TLS",
        "value": os.environ.get("EMAIL_USE_TLS", "1"),
        "category": "SMTP",
        "is_encrypted": False,
    },
    {
        "key": "EMAIL_USE_SSL",
        "value": os.environ.get("EMAIL_USE_SSL", "0"),
        "category": "SMTP",
        "is_encrypted": False,
    },
]

llm_config_variables = [
    {
        "key": "LLM_API_KEY",
        "value": os.environ.get("LLM_API_KEY"),
        "category": "AI",
        "is_encrypted": True,
    },
    {
        "key": "LLM_PROVIDER",
        "value": os.environ.get("LLM_PROVIDER", "openai"),
        "category": "AI",
        "is_encrypted": False,
    },
    {
        "key": "LLM_MODEL",
        "value": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        "category": "AI",
        "is_encrypted": False,
    },
    # Deprecated, use LLM_MODEL
    {
        "key": "GPT_ENGINE",
        "value": os.environ.get("GPT_ENGINE", "gpt-3.5-turbo"),
        "category": "AI",
        "is_encrypted": False,
    },
]

unsplash_config_variables = [
    {
        "key": "UNSPLASH_ACCESS_KEY",
        "value": os.environ.get("UNSPLASH_ACCESS_KEY", ""),
        "category": "UNSPLASH",
        "is_encrypted": True,
    },
]

core_config_variables = [
    *authentication_config_variables,
    *workspace_management_config_variables,
    *github_config_variables,
    *gitlab_config_variables,
    *gitea_config_variables,
    *smtp_config_variables,
    *llm_config_variables,
    *unsplash_config_variables,
]
