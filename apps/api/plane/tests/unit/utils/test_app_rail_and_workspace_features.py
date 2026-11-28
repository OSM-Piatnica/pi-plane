# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for the key lists the API validates app preferences and feature switches against."""

import pytest

from plane.utils import app_rail, workspace_features
from plane.utils.app_rail import is_app_rail_app_key, is_app_rail_preference_key
from plane.utils.workspace_features import (
    available_workspace_feature_keys,
    enabled_workspace_feature_keys,
    is_available_workspace_feature,
    is_known_workspace_feature,
    workspace_feature_states,
)


class _Row:
    def __init__(self, key, is_enabled):
        self.key = key
        self.is_enabled = is_enabled


class _Manager:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def all(self):
        self.calls += 1
        return self.rows


class _Workspace:
    def __init__(self, *rows):
        self.workspace_features = _Manager(list(rows))


def _only_available(monkeypatch, *keys):
    """Makes exactly ``keys`` available for the test, whatever is built."""
    for key in workspace_features.WORKSPACE_FEATURES:
        monkeypatch.setitem(workspace_features.WORKSPACE_FEATURES, key, key in keys)


@pytest.mark.unit
class TestAppRailKeys:
    def test_projects_and_initiatives_are_the_apps(self):
        assert is_app_rail_app_key("projects")
        assert is_app_rail_app_key("initiatives")
        assert not is_app_rail_app_key("approvals")

    @pytest.mark.parametrize("value", [None, "", 5, ["projects"], {"projects": 1}, "Projects", " projects"])
    def test_other_values_are_not_app_keys(self, value):
        assert not is_app_rail_app_key(value)

    def test_preference_key_needs_the_prefix_and_a_known_app(self):
        assert is_app_rail_preference_key("app_rail:projects")
        assert is_app_rail_preference_key("app_rail:initiatives")
        for key in [
            "projects",
            "app_rail:",
            "app_rail",
            "app_rail:approvals",
            "app_rail:projects:x",
            "drafts",
            None,
            3,
        ]:
            assert not is_app_rail_preference_key(key)

    def test_a_registered_app_is_accepted(self, monkeypatch):
        monkeypatch.setattr(app_rail, "APP_RAIL_APP_KEYS", ("projects", "approvals"))

        assert is_app_rail_app_key("approvals")
        assert is_app_rail_preference_key("app_rail:approvals")


@pytest.mark.unit
class TestWorkspaceFeatureKeys:
    def test_as_shipped_only_initiatives_and_raci_are_available(self):
        assert list(workspace_features.WORKSPACE_FEATURES) == ["lite", "approvals", "initiatives", "wiki", "raci"]
        assert available_workspace_feature_keys() == ["initiatives", "raci"]
        assert is_available_workspace_feature("initiatives")
        assert is_known_workspace_feature("wiki")
        assert not is_available_workspace_feature("wiki")
        assert is_available_workspace_feature("raci")
        assert not is_known_workspace_feature("unknown")
        assert not is_available_workspace_feature("unknown")

    def test_a_row_of_a_feature_that_is_not_built_is_not_reported(self):
        workspace = _Workspace(_Row("approvals", True), _Row("wiki", True))

        assert enabled_workspace_feature_keys(workspace) == []
        assert workspace_feature_states(workspace) == {"initiatives": False, "raci": False}

    def test_nothing_is_enabled_and_nothing_is_queried_while_nothing_is_available(self, monkeypatch):
        _only_available(monkeypatch)
        workspace = _Workspace(_Row("approvals", True), _Row("wiki", True))

        assert enabled_workspace_feature_keys(workspace) == []
        assert workspace_feature_states(workspace) == {}
        assert workspace.workspace_features.calls == 0

    def test_enabled_keys_are_the_available_ones_that_are_switched_on(self, monkeypatch):
        _only_available(monkeypatch, "approvals", "lite")
        # wiki is on in the table but not available; lite is available but off; a stray key is ignored
        workspace = _Workspace(
            _Row("wiki", True), _Row("approvals", True), _Row("lite", False), _Row("removed_feature", True)
        )

        assert available_workspace_feature_keys() == ["lite", "approvals"]
        assert enabled_workspace_feature_keys(workspace) == ["approvals"]
        assert workspace_feature_states(workspace) == {"lite": False, "approvals": True}

    def test_a_missing_row_means_off(self, monkeypatch):
        _only_available(monkeypatch, "approvals")

        assert workspace_feature_states(_Workspace()) == {"approvals": False}
