# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The MCP server (signed in with Entra) shows each person the same work items as the Copilot connector."""

from types import SimpleNamespace
from unittest import mock

import pytest

pytest.importorskip("mcp")
import plane_mcp_server as srv  # noqa: E402

from test_access import A, B, GONE, GUEST, LITE, fake_get  # noqa: E402

ITEMS = [
    {"id": "i1", "created_by": B, "assignees": [{"id": A}], "group_assignee_ids": []},
    {"id": "i2", "created_by": GUEST, "assignees": [{"id": GUEST}], "group_assignee_ids": []},
    {"id": "i3", "created_by": A, "assignees": [], "group_assignee_ids": ["g-1"]},
    {"id": "i4", "created_by": A, "assignees": [{"id": B}], "group_assignee_ids": []},
    {"id": "i5", "created_by": B, "assignees": [], "group_assignee_ids": []},
    {"id": "i6", "created_by": B, "assignees": [{"id": GONE}], "group_assignee_ids": []},
]


def fake_get_all(path, params=None, cap=None):
    if path.endswith("/project-members-lite/"):
        return LITE
    if path.endswith("/work-items/"):
        return ITEMS
    raise AssertionError(path)


def visible(email, mode, project=None):
    srv._cache.clear()
    token = SimpleNamespace(claims={"email": email})
    with mock.patch.object(srv, "_get_all", fake_get_all), \
            mock.patch.object(srv, "_get", lambda path, params=None: fake_get("x" + path, params)), \
            mock.patch.object(srv, "AUTH_MODE", "entra"), mock.patch.object(srv, "VISIBILITY", mode), \
            mock.patch.object(srv, "get_access_token", lambda: token):
        return [item["id"] for item in srv._visible_items(project or {"id": "p1"})]


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("A@x.test", ["i1"]),  # only what is assigned to Anna
        ("b@x.test", ["i3", "i4"]),  # own and through the group
        ("c@x.test", ["i3"]),  # only through the group
        ("guest@x.test", ["i2"]),
        ("bot@x.test", []),
        ("gone@x.test", []),
    ],
)
def test_precise(email, expected):
    assert visible(email, "precise") == expected


def test_the_project_lead_also_sees_the_unassigned_ones():
    assert visible("a@x.test", "precise", {"id": "p1", "project_lead": A}) == ["i1", "i5", "i6"]
    assert visible("b@x.test", "precise", {"id": "p1", "project_lead": A}) == ["i3", "i4"]


def test_project_mode_is_like_plane():
    assert visible("a@x.test", "project") == [item["id"] for item in ITEMS]
    assert visible("guest@x.test", "project") == ["i2"]
