# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The connector reads its settings at import time; the tests use made-up values and never call Plane or Graph."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.update(
    {
        "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000000",
        "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000001",
        "AZURE_CLIENT_SECRET": "test-secret",
        "GRAPH_CONNECTION_ID": "testconnection",
        "PLANE_BASE_URL": "https://plane.example.test",
        "PLANE_API_URL": "http://api:8000",
        "PLANE_WORKSPACE_SLUG": "test",
        "PLANE_API_TOKEN": "plane_api_test",
        "DEFAULT_ACL_TYPE": "precise",
        "STATE_DIR": str(ROOT / "tests" / ".state"),
        "PLANE_SSL_VERIFY": "true",
    }
)
