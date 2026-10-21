# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import cycle, issue, module, project, view, workspace

# The work item display filters each model creates for a new user or entity. Project and workspace keep
# them inside their default properties.
DEFAULT_DISPLAY_FILTERS = {
    "cycle": cycle.get_default_display_filters,
    "issue": issue.get_default_display_filters,
    "module": module.get_default_display_filters,
    "view": view.get_default_display_filters,
    "project": lambda: project.get_default_props()["display_filters"],
    "workspace": lambda: workspace.get_default_props()["display_filters"],
    "workspace_views": lambda: workspace.get_default_display_filters()["display_filters"],
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(DEFAULT_DISPLAY_FILTERS))
class TestDefaultWorkItemDisplayFilters:
    """New work item lists show the oldest work item first and hide sub-work items."""

    def test_order_by_is_oldest_first(self, name):
        assert DEFAULT_DISPLAY_FILTERS[name]()["order_by"] == "created_at"

    def test_sub_work_items_are_hidden(self, name):
        assert DEFAULT_DISPLAY_FILTERS[name]()["sub_issue"] is False
