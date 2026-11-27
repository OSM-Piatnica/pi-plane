# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A sync run: what is sent, what is removed from Copilot, and what is skipped (nothing is sent to Graph)."""

import json
import os
from datetime import datetime, timedelta
from unittest import mock

import pytest
import requests

import sync_service

P1, P2 = {"id": "p1", "name": "P1"}, {"id": "p2", "name": "P2"}


def it(item_id, **extra):
    return {"id": item_id, "name": item_id, **extra}


@pytest.fixture
def run(tmp_path):
    state_file = tmp_path / "sync_state.json"

    def _run(projects, items_by_project, previous=None, allow=False, unreadable=(), full=False, keep_state=False):
        if not keep_state:
            state_file.unlink(missing_ok=True)
            if previous is not None:
                state_file.write_text(json.dumps({"connection_id": sync_service.settings.GRAPH_CONNECTION_ID,
                                                  "items": previous}), encoding="utf-8")
        pushed, removed = [], []

        def list_items(pid):
            if pid in unreadable:
                response = requests.Response()
                response.status_code = 403
                raise requests.exceptions.HTTPError(response=response)
            return items_by_project[pid]

        access = mock.MagicMock()
        access.acl_for.side_effect = lambda item: [] if item.get("hidden") else [{"type": "user", "value": "x"}]
        access.creator_name.return_value = ""
        with mock.patch.object(sync_service, "STATE_FILE", state_file), \
                mock.patch.object(sync_service, "LOCK_FILE", tmp_path / "sync.lock"), \
                mock.patch.object(sync_service, "_check_graph_ready", lambda: None), \
                mock.patch.object(sync_service.plane_labels, "ensure_fresh", lambda *args: None), \
                mock.patch.object(sync_service, "list_projects", lambda: projects), \
                mock.patch.object(sync_service, "ProjectAccess", lambda project: access), \
                mock.patch.object(sync_service, "list_all_work_items", list_items), \
                mock.patch.object(sync_service, "_push_item", lambda e: pushed.append(e["id"]) or True), \
                mock.patch.object(sync_service, "_remove_item", lambda gid, reason: removed.append(gid) or True):
            code = sync_service.run_sync(allow_mass_delete=allow, full=full)
        items = json.loads(state_file.read_text(encoding="utf-8"))["items"]
        return code, pushed, removed, {gid: entry["project"] for gid, entry in items.items()}

    _run.lock = tmp_path / "sync.lock"
    return _run


class TestDeletedInPlane:
    def test_first_run_remembers_what_was_sent(self, run):
        code, pushed, removed, state = run([P1], {"p1": [it("a"), it("b")]})
        assert code == 0 and sorted(pushed) == ["p1_a", "p1_b"] and not removed
        assert set(state) == {"p1_a", "p1_b"}

    def test_a_work_item_deleted_in_plane_leaves_copilot(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        _, _, removed, state = run([P1], {"p1": [it("a")]}, keep_state=True)
        assert removed == ["p1_b"] and set(state) == {"p1_a"}

    def test_a_deleted_project_leaves_copilot(self, run):
        _, _, removed, state = run([P1], {"p1": [it("a")]}, {"p1_a": "p1", "p2_x": "p2"})
        assert removed == ["p2_x"] and set(state) == {"p1_a"}

    def test_a_project_that_could_not_be_read_is_left_alone(self, run):
        previous = {"p1_a": "p1", "p2_x": "p2"}
        code, _, removed, state = run([P1, P2], {"p1": [it("a")]}, previous, unreadable={"p2"})
        assert removed == [] and state == previous
        assert code == 1  # reported, for monitoring

    def test_a_work_item_nobody_may_see_is_removed(self, run):
        _, _, removed, state = run([P1], {"p1": [it("a"), it("h", hidden=True)]}, {"p1_a": "p1", "p1_h": "p1"})
        assert removed == ["p1_h"] and set(state) == {"p1_a"}

    def test_a_mass_disappearance_deletes_nothing_without_permission(self, run):
        previous = {f"p1_{n}": "p1" for n in range(40)}
        code, _, removed, state = run([P1], {"p1": [it("0")]}, previous)
        assert removed == [] and set(state) == set(previous) and code == 1
        _, _, removed, state = run([P1], {"p1": [it("0")]}, previous, allow=True)
        assert len(removed) == 39 and set(state) == {"p1_0"}


class TestFrequentRuns:
    def test_unchanged_work_items_are_not_sent_again(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        _, pushed, _, _ = run([P1], {"p1": [it("a"), it("b")]}, keep_state=True)
        assert pushed == []

    def test_only_the_changed_work_item_is_sent(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        _, pushed, _, _ = run([P1], {"p1": [it("a"), it("b", name="nowa nazwa")]}, keep_state=True)
        assert pushed == ["p1_b"]

    def test_full_sends_everything(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        _, pushed, _, _ = run([P1], {"p1": [it("a"), it("b")]}, keep_state=True, full=True)
        assert sorted(pushed) == ["p1_a", "p1_b"]

    def test_a_running_sync_is_not_started_twice(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        run.lock.write_text("123")
        code, pushed, removed, state = run([P1], {"p1": [it("a")]}, keep_state=True)
        assert code == 0 and pushed == [] and removed == [] and "p1_b" in state
        assert run.lock.exists()

    def test_a_stale_lock_is_removed(self, run):
        run([P1], {"p1": [it("a"), it("b")]})
        run.lock.write_text("123")
        old = (datetime.now() - timedelta(hours=5)).timestamp()
        os.utime(run.lock, (old, old))
        _, _, removed, _ = run([P1], {"p1": [it("a")]}, keep_state=True)
        assert removed == ["p1_b"] and not run.lock.exists()


def test_an_unknown_acl_mode_stops_the_run(run):
    with mock.patch.object(sync_service.settings, "DEFAULT_ACL_TYPE", "everybody"):
        assert sync_service._run_sync(False, False) == 1
