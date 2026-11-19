# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""list_projects reads every page, or the sync would delete the work items of the projects on later pages."""

from unittest import mock

import plane_client


def test_list_projects_follows_the_cursor():
    pages = {
        None: {"results": [{"id": "p1"}], "next_page_results": True, "next_cursor": "c2"},
        "c2": {"results": [{"id": "p2"}], "next_page_results": False, "next_cursor": None},
    }
    calls = []

    def fake_get(url, params=None):
        calls.append(params.get("cursor"))
        return pages[params.get("cursor")]

    with mock.patch.object(plane_client, "_get", fake_get):
        assert [p["id"] for p in plane_client.list_projects()] == ["p1", "p2"]
    assert calls == [None, "c2"]
