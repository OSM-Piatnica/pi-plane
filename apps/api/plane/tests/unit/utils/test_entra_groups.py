# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Which kinds of Entra data become groups: the classification of Graph groups and the mapping of the rest."""

from unittest.mock import patch

import pytest

from plane.authentication.provider.oidc import client, groups
from plane.authentication.provider.oidc.groups import ExternalGroup
from plane.authentication.provider.oidc.providers import EntraSpec

SECURITY = {"id": "AAAA0000-0000-0000-0000-000000000001", "displayName": "Sec", "securityEnabled": True}
MAIL_SECURITY = {
    "id": "aaaa0000-0000-0000-0000-000000000002",
    "displayName": "MailSec",
    "securityEnabled": True,
    "mailEnabled": True,
}
M365 = {
    "id": "aaaa0000-0000-0000-0000-000000000003",
    "displayName": "Team",
    "securityEnabled": False,
    "mailEnabled": True,
    "groupTypes": ["Unified"],
}
M365_SECURITY = {
    **M365,
    "id": "aaaa0000-0000-0000-0000-000000000004",
    "displayName": "Team sec",
    "securityEnabled": True,
}
LIST = {
    "id": "aaaa0000-0000-0000-0000-000000000005",
    "displayName": "All staff",
    "securityEnabled": False,
    "mailEnabled": True,
    "groupTypes": [],
}
UNKNOWN = {"id": "aaaa0000-0000-0000-0000-000000000006", "displayName": "Plain"}
UNIT = {"id": "BBBB0000-0000-0000-0000-000000000001", "displayName": "Poland"}

GROUPS_URL = groups.GRAPH_GROUPS_URL
UNITS_URL = groups.GRAPH_ADMIN_UNITS_URL
PROFILE_URL = groups.GRAPH_PROFILE_URL


class Graph:
    """Answers Graph calls by url; an exception as an answer is raised."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, url, token, params=None):
        self.calls.append((url, params))
        answer = self.answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer


def fetch(answers, kinds=None):
    graph = Graph(answers)
    with patch.object(client, "get_json_with_bearer", side_effect=graph):
        return groups.fetch_entra_groups("token", kinds), graph


@pytest.mark.unit
class TestClassifyGroup:
    @pytest.mark.parametrize(
        "entry, kind",
        [
            (SECURITY, groups.KIND_SECURITY),
            (MAIL_SECURITY, groups.KIND_SECURITY),
            (M365, groups.KIND_MICROSOFT_365),
            # a Microsoft 365 group is one even when it is security-enabled as well
            (M365_SECURITY, groups.KIND_MICROSOFT_365),
            (LIST, groups.KIND_DISTRIBUTION),
            # nothing said: taken as it always was
            (UNKNOWN, groups.KIND_SECURITY),
        ],
    )
    def test_kind_of_a_group(self, entry, kind):
        assert groups.classify_group(entry) == kind


@pytest.mark.unit
class TestEntraKinds:
    def test_defaults_keep_every_group_and_nothing_else(self):
        assert groups.entra_kinds({}) == {groups.KIND_SECURITY, groups.KIND_MICROSOFT_365, groups.KIND_DISTRIBUTION}
        assert groups.entra_kinds({"GROUPS_SECURITY": "", "GROUPS_ADMIN_UNITS": None}) == set(groups.GROUP_KINDS)

    def test_switches_are_read_from_the_settings(self):
        config = {"GROUPS_SECURITY": "0", "GROUPS_DISTRIBUTION": "0", "GROUPS_ADMIN_UNITS": "1", "GROUPS_COMPANY": "1"}
        assert groups.entra_kinds(config) == {groups.KIND_MICROSOFT_365, groups.KIND_ADMIN_UNITS, groups.KIND_COMPANY}

    def test_the_spec_declares_the_six_switches_with_those_defaults(self):
        fields = {field.name: field for field in EntraSpec().fields}
        expected = {
            "GROUPS_SECURITY": "1",
            "GROUPS_MICROSOFT_365": "1",
            "GROUPS_DISTRIBUTION": "1",
            "GROUPS_ADMIN_UNITS": "0",
            "GROUPS_DEPARTMENT": "0",
            "GROUPS_COMPANY": "0",
        }
        for name, default in expected.items():
            assert fields[name].kind == "switch" and fields[name].default == default
        assert fields["SYNC_GROUPS"].kind == "switch"

    def test_the_administrative_unit_permission_is_only_asked_for_when_switched_on(self):
        spec = EntraSpec()
        on = {"SYNC_GROUPS": "1"}
        assert groups.ENTRA_ADMIN_UNITS_SCOPE not in spec.request_scopes(on)
        assert groups.ENTRA_GROUPS_SCOPE in spec.request_scopes(on)
        assert groups.ENTRA_ADMIN_UNITS_SCOPE in spec.request_scopes({**on, "GROUPS_ADMIN_UNITS": "1"})
        # the master switch off: nothing is asked for
        assert spec.request_scopes({"SYNC_GROUPS": "0", "GROUPS_ADMIN_UNITS": "1"}) == spec.scopes


@pytest.mark.unit
class TestFetchEntraGroups:
    def test_every_kind_of_group_is_taken_by_default_with_lower_cased_ids(self):
        result, graph = fetch({GROUPS_URL: {"value": [SECURITY, M365, LIST]}})

        assert result == [
            ExternalGroup("aaaa0000-0000-0000-0000-000000000001", "Sec"),
            ExternalGroup("aaaa0000-0000-0000-0000-000000000003", "Team"),
            ExternalGroup("aaaa0000-0000-0000-0000-000000000005", "All staff"),
        ]
        # only the groups were asked for, with the fields that tell the kind and no others
        assert [url for url, _ in graph.calls] == [GROUPS_URL]
        assert graph.calls[0][1]["$select"] == "id,displayName,securityEnabled,mailEnabled,groupTypes"

    def test_the_switches_filter_the_kinds(self):
        page = {"value": [SECURITY, MAIL_SECURITY, M365, M365_SECURITY, LIST]}

        only_security, _ = fetch({GROUPS_URL: page}, {groups.KIND_SECURITY})
        only_365, _ = fetch({GROUPS_URL: page}, {groups.KIND_MICROSOFT_365})
        only_lists, _ = fetch({GROUPS_URL: page}, {groups.KIND_DISTRIBUTION})

        assert [g.name for g in only_security] == ["Sec", "MailSec"]
        assert [g.name for g in only_365] == ["Team", "Team sec"]
        assert [g.name for g in only_lists] == ["All staff"]

    def test_no_group_kind_means_no_call_for_groups(self):
        result, graph = fetch({PROFILE_URL: {"department": "Sales"}}, {groups.KIND_DEPARTMENT})

        assert result == [ExternalGroup("department:sales", "Department: Sales")]
        assert [url for url, _ in graph.calls] == [PROFILE_URL]
        assert graph.calls[0][1] == {"$select": "department,companyName"}

    def test_administrative_units_get_their_own_ids_and_names(self):
        result, graph = fetch({UNITS_URL: {"value": [UNIT]}}, {groups.KIND_ADMIN_UNITS})

        assert result == [ExternalGroup("au:bbbb0000-0000-0000-0000-000000000001", "Administrative unit: Poland")]
        assert graph.calls[0][1]["$select"] == "id,displayName"

    def test_department_and_company_are_one_group_per_distinct_value(self):
        profile = {"department": "  Sales   North ", "companyName": "Acme"}
        result, _ = fetch({PROFILE_URL: profile}, {groups.KIND_DEPARTMENT, groups.KIND_COMPANY})

        assert sorted(result, key=lambda g: g.id) == [
            ExternalGroup("company:acme", "Company: Acme"),
            ExternalGroup("department:sales north", "Department: Sales North"),
        ]

    @pytest.mark.parametrize("profile", [{}, {"department": None, "companyName": ""}, {"department": "   "}])
    def test_a_blank_or_missing_attribute_gives_no_group(self, profile):
        result, _ = fetch({PROFILE_URL: profile}, {groups.KIND_DEPARTMENT, groups.KIND_COMPANY})

        assert result == []

    def test_a_kind_that_is_off_is_not_read(self):
        result, graph = fetch({GROUPS_URL: {"value": [SECURITY]}}, {groups.KIND_SECURITY})

        assert len(result) == 1
        assert [url for url, _ in graph.calls] == [GROUPS_URL]

    def test_a_refused_administrative_unit_call_keeps_the_other_kinds(self):
        answers = {
            GROUPS_URL: {"value": [SECURITY]},
            PROFILE_URL: {"department": "Sales"},
            UNITS_URL: client.OidcProtocolError("Provider returned HTTP 403"),
        }
        kinds = {groups.KIND_SECURITY, groups.KIND_DEPARTMENT, groups.KIND_ADMIN_UNITS}

        result, _ = fetch(answers, kinds)

        assert {g.id for g in result} == {"aaaa0000-0000-0000-0000-000000000001", "department:sales"}

    def test_a_failing_groups_call_reads_nothing_so_that_what_was_mirrored_stays(self):
        answers = {
            GROUPS_URL: client.OidcProtocolError("Provider returned HTTP 500"),
            UNITS_URL: {"value": [UNIT]},
        }

        result, _ = fetch(answers, {groups.KIND_SECURITY, groups.KIND_ADMIN_UNITS})

        assert result is None

    def test_a_failing_profile_call_reads_nothing(self):
        result, _ = fetch({PROFILE_URL: client.OidcProtocolError("down")}, {groups.KIND_DEPARTMENT})

        assert result is None

    def test_paging_links_to_another_host_are_not_followed(self):
        page = {"value": [SECURITY], "@odata.nextLink": "https://evil.example.com/steal"}

        result, graph = fetch({GROUPS_URL: page})

        assert result is None
        assert len(graph.calls) == 1

    def test_no_token_reads_nothing(self):
        assert groups.fetch_entra_groups(None) is None
