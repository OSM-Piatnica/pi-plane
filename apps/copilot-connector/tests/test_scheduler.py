# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The service sets up Microsoft Graph by itself and keeps running when one run fails."""

from unittest import mock

import pytest

import scheduler


def services(states, sync_code=0):
    sync = mock.Mock()
    sync.schema_status.side_effect = states
    sync.run_sync.return_value = sync_code
    graph = mock.Mock()
    return sync, graph


def test_ready_graph_just_syncs():
    sync, graph = services([("ok", None)])
    assert scheduler.run_once(sync, graph) == 0
    graph.create_schema.assert_not_called()
    sync.run_sync.assert_called_once()


def test_missing_connection_or_schema_is_created_first():
    sync, graph = services([("missing", ["createdBy"]), ("ok", None)])
    assert scheduler.run_once(sync, graph) == 0
    graph.create_connection.assert_called_once()
    graph.create_schema.assert_called_once()
    sync.run_sync.assert_called_once()


def test_graph_outage_skips_the_run():
    sync, graph = services([("error", "API konektorow Microsoft Graph zwraca blad 504")])
    assert scheduler.run_once(sync, graph) == 1
    sync.run_sync.assert_not_called()


def test_an_exception_does_not_stop_the_service():
    sync, graph = services([("ok", None)])
    sync.run_sync.side_effect = RuntimeError("boom")
    assert scheduler.run_once(sync, graph) == 1


@pytest.mark.parametrize(("value", "minutes"), [("", 30), ("15", 15), ("1", 5), ("abc", 30)])
def test_interval(monkeypatch, value, minutes):
    monkeypatch.setenv("COPILOT_SYNC_INTERVAL_MINUTES", value)
    assert scheduler._interval_seconds() == minutes * 60
