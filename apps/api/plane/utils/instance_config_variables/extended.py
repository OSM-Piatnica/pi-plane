# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Python imports
import os

# Module imports
from plane.authentication.provider.oidc.registry import oidc_config_variables

# Documents in SharePoint through Microsoft Graph, signed in as the application itself (docs/sharepoint.md). Set in
# the admin app under Integrations → SharePoint.
sharepoint_config_variables = [
    {
        "key": "IS_SHAREPOINT_ENABLED",
        "value": os.environ.get("IS_SHAREPOINT_ENABLED", "0"),
        "category": "SHAREPOINT",
        "is_encrypted": False,
    },
    {
        # The directory (tenant) ID of the Entra tenant the app registration lives in
        "key": "SHAREPOINT_TENANT_ID",
        "value": os.environ.get("SHAREPOINT_TENANT_ID", ""),
        "category": "SHAREPOINT",
        "is_encrypted": False,
    },
    {
        # The application (client) ID of the app registration
        "key": "SHAREPOINT_CLIENT_ID",
        "value": os.environ.get("SHAREPOINT_CLIENT_ID", ""),
        "category": "SHAREPOINT",
        "is_encrypted": False,
    },
    {
        "key": "SHAREPOINT_CLIENT_SECRET",
        "value": os.environ.get("SHAREPOINT_CLIENT_SECRET", ""),
        "category": "SHAREPOINT",
        "is_encrypted": True,
    },
    {
        # Largest file for SharePoint in bytes. Empty means the default of 500 MB. Apart from FILE_SIZE_LIMIT.
        "key": "SHAREPOINT_MAX_FILE_SIZE",
        "value": os.environ.get("SHAREPOINT_MAX_FILE_SIZE", ""),
        "category": "SHAREPOINT",
        "is_encrypted": False,
    },
]

extended_config_variables = [*oidc_config_variables(), *sharepoint_config_variables]
