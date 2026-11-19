# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Who sees a work item in Copilot (DEFAULT_ACL_TYPE), and how Plane members and groups are read."""

from unittest import mock

import pytest
import requests

import plane_client
import sync_service

A, B, C, GUEST, BOT, GONE, NOENTRA = "u-a", "u-b", "u-c", "u-guest", "u-bot", "u-gone", "u-noentra"
LITE = [
    {"id": A, "email": "A@x.test", "display_name": "Anna", "role": 20, "is_active": True, "is_bot": False},
    {"id": B, "email": "b@x.test", "display_name": "Bartek", "role": 15, "is_active": True, "is_bot": False},
    {"id": C, "email": "c@x.test", "display_name": "Celina", "role": 15, "is_active": True, "is_bot": False},
    {"id": GUEST, "email": "guest@x.test", "display_name": "Gosc", "role": 5, "is_active": True, "is_bot": False},
    {"id": BOT, "email": "bot@x.test", "display_name": "Pi-Plane API", "role": 15, "is_active": True, "is_bot": True},
    {"id": GONE, "email": "gone@x.test", "display_name": "Byly", "role": 15, "is_active": False, "is_bot": False},
    {"id": NOENTRA, "email": "external@x.test", "display_name": "Ext", "role": 15, "is_active": True, "is_bot": False},
]
ENTRA = {"a@x.test": "oid-a", "b@x.test": "oid-b", "c@x.test": "oid-c", "guest@x.test": "oid-guest",
         "bot@x.test": "oid-bot", "gone@x.test": "oid-gone"}
GROUPS = {"g-1": {C, B}}


def fake_get(url, params=None):
    if url.endswith("/project-members-lite/"):
        return {"results": LITE, "next_page_results": False}
    if url.endswith("/groups/"):
        assert params == {"assignable": 1, "members": 1}
        return [{"id": "g-1", "name": "Magazyn", "member_ids": sorted(GROUPS["g-1"])}]
    raise AssertionError(url)


def http_error(code):
    response = requests.Response()
    response.status_code = code
    return requests.exceptions.HTTPError(response=response)


@pytest.fixture
def people():
    with mock.patch.object(plane_client, "_get", fake_get):
        return plane_client.list_project_people("p1")


def item(created_by, assignees=(), groups=()):
    return {"id": "i", "created_by": created_by, "assignees": [{"id": a} for a in assignees],
            "group_assignee_ids": list(groups)}


def access(people, mode, project=None, groups=GROUPS):
    sync_service._object_ids.clear()
    with mock.patch.object(sync_service.settings, "DEFAULT_ACL_TYPE", mode), \
            mock.patch.object(sync_service, "list_project_people", lambda pid: people), \
            mock.patch.object(sync_service, "list_group_members", lambda pid: groups), \
            mock.patch.object(sync_service, "resolve_user_object_id", lambda e: ENTRA.get(e)):
        acc = sync_service.ProjectAccess(project or {"id": "p1", "name": "P"})
    acc._groups = groups if mode == "precise" else None
    return acc


def oids(acl):
    return sorted(e["value"] for e in acl)


class TestPlaneClient:
    def test_members_skip_bots_and_inactive_people(self):
        with mock.patch.object(plane_client, "_get", fake_get):
            members = plane_client.list_project_members("p1")
        assert {m["id"] for m in members} == {A, B, C, GUEST, NOENTRA}
        assert next(m for m in members if m["id"] == A)["email"] == "a@x.test"

    def test_people_keep_inactive_ones_for_author_names(self, people):
        assert GONE in {p["id"] for p in people}

    def test_group_members(self):
        with mock.patch.object(plane_client, "_get", fake_get):
            assert plane_client.list_group_members("p1") == {"g-1": GROUPS["g-1"]}

    def test_older_plane_without_members_lite(self):
        def old(url, params=None):
            if url.endswith("/project-members-lite/"):
                raise http_error(404)
            return [{"id": B, "email": "b@x.test", "display_name": "B"}]

        with mock.patch.object(plane_client, "_get", old):
            members = plane_client.list_project_members("p1")
        assert [m["id"] for m in members] == [B] and members[0]["role"] is None

    def test_api_url_is_the_internal_one(self):
        assert plane_client._base_url() == "http://api:8000/api/v1/workspaces/test"

    def test_waits_and_retries_after_429(self):
        limited = mock.Mock(status_code=429, headers={"Retry-After": "1"})
        ok = mock.Mock(status_code=200, headers={})
        ok.json.return_value = {"results": []}
        with mock.patch.object(plane_client.requests, "get", side_effect=[limited, ok]) as get, \
                mock.patch.object(plane_client.time, "sleep") as sleep:
            assert plane_client._get("http://api:8000/x") == {"results": []}
        assert get.call_count == 2 and sleep.called


class TestPreciseAcl:
    """Only the people assigned to a work item see it; the project lead sees the unassigned ones."""

    def test_assignee_only(self, people):
        acc = access(people, "precise")
        assert oids(acc.acl_for(item(B, [A]))) == ["oid-a"]

    def test_author_who_is_not_assigned_does_not_see_it(self, people):
        assert oids(access(people, "precise").acl_for(item(A, [B]))) == ["oid-b"]

    def test_unassigned_without_lead_nobody(self, people):
        assert access(people, "precise").acl_for(item(A)) == []

    def test_group_assignment_reaches_its_members(self, people):
        assert oids(access(people, "precise").acl_for(item(A, groups=["g-1"]))) == ["oid-b", "oid-c"]

    def test_unknown_group_members_nobody(self, people):
        assert access(people, "precise", groups={}).acl_for(item(A, groups=["g-1"])) == []

    @pytest.mark.parametrize("who", [BOT, GONE, NOENTRA])
    def test_bots_inactive_and_people_without_entra_see_nothing(self, people, who):
        assert access(people, "precise").acl_for(item(A, [who])) == []

    def test_guest_sees_only_what_plane_shows_them(self, people):
        acc = access(people, "precise")
        assert acc.acl_for(item(A, [GUEST])) == []
        assert oids(acc.acl_for(item(GUEST, [GUEST]))) == ["oid-guest"]
        acc = access(people, "precise", {"id": "p1", "name": "P", "guest_view_all_features": True})
        assert oids(acc.acl_for(item(A, [GUEST]))) == ["oid-guest"]

    def test_author_name(self, people):
        acc = access(people, "precise")
        assert acc.creator_name(item(A)) == "Anna" and acc.creator_name(item(GONE)) == "Byly"


class TestProjectLead:
    LED = {"id": "p1", "name": "P", "project_lead": B}

    def test_unassigned_goes_to_the_lead(self, people):
        assert oids(access(people, "precise", self.LED).acl_for(item(A))) == ["oid-b"]

    def test_the_lead_does_not_see_other_peoples_items(self, people):
        assert oids(access(people, "precise", self.LED).acl_for(item(A, [A]))) == ["oid-a"]

    @pytest.mark.parametrize("who", [GONE, BOT])
    def test_assigned_only_to_somebody_gone_goes_to_the_lead(self, people, who):
        assert oids(access(people, "precise", self.LED).acl_for(item(A, [who]))) == ["oid-b"]

    def test_group_assignment_does_not_add_the_lead(self, people):
        assert oids(access(people, "precise", self.LED).acl_for(item(A, groups=["g-1"]))) == ["oid-b", "oid-c"]

    def test_lead_as_object_and_inactive_lead(self, people):
        assert oids(access(people, "precise", {"id": "p1", "project_lead": {"id": A}}).acl_for(item(B))) == ["oid-a"]
        assert access(people, "precise", {"id": "p1", "project_lead": GONE}).acl_for(item(A)) == []


class TestOtherModes:
    def test_project_mode_is_like_plane(self, people):
        acc = access(people, "project")
        assert oids(acc.acl_for(item(A))) == ["oid-a", "oid-b", "oid-c"]
        assert "oid-guest" in oids(acc.acl_for(item(GUEST)))

    def test_everyone(self, people):
        assert access(people, "everyone").acl_for(item(A))[0]["type"] == "everyone"


def test_external_item_carries_the_full_work_item():
    ext = sync_service._map_work_item_to_external_item(
        {"id": "p1", "name": "Scan box", "identifier": "SB"},
        {"id": "i1", "name": "Montaz", "sequence_id": 3, "state": {"name": "In Progress"}, "priority": "high",
         "assignees": [{"id": A, "display_name": "Anna"}], "description_html": "<p>Opis</p>",
         "created_at": "2026-01-01T00:00:00Z"},
        [{"type": "user", "value": "oid-a"}], "Bartek")
    assert ext["id"] == "p1_i1"
    assert ext["properties"]["createdBy"] == "Bartek"
    assert ext["properties"]["itemKey"] == "SB-3"
    assert ext["properties"]["url"] == "https://plane.example.test/test/projects/p1/issues/i1"
    for text in ("Status: In Progress", "Przypisane do: Anna", "Utworzone przez: Bartek", "Opis"):
        assert text in ext["content"]["value"]
