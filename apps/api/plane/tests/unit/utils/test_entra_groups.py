# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Which kinds of Entra data become groups: the classification of Graph groups and the mapping of the rest."""

from unittest.mock import patch

import pytest

from plane.authentication.provider.oidc import client, groups
from plane.authentication.provider.oidc.groups import ExternalGroup
from plane.authentication.provider.oidc.providers import EntraSpec
from plane.utils.user_groups import MAX_GROUP_DEPTH

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
            "GROUPS_OFFICE": "0",
            "GROUPS_ORG_UNITS": "0",
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
        assert graph.calls[0][1] == {"$select": "department"}

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


PL_SALES = "CN=Pat Kowalski,OU=Sales,OU=Poland,DC=corp,DC=local"


@pytest.mark.unit
class TestDistinguishedName:
    def test_pairs_are_in_the_order_written_with_lower_cased_types(self):
        assert groups.parse_distinguished_name(PL_SALES) == [
            ("cn", "Pat Kowalski"),
            ("ou", "Sales"),
            ("ou", "Poland"),
            ("dc", "corp"),
            ("dc", "local"),
        ]

    def test_odd_spacing_and_case(self):
        assert groups.parse_distinguished_name("cn=Pat ,  Ou = Sales  ,oU=Poland ,dc=x") == [
            ("cn", "Pat"),
            ("ou", "Sales"),
            ("ou", "Poland"),
            ("dc", "x"),
        ]

    def test_escaped_separators_and_hex_escapes(self):
        pairs = groups.parse_distinguished_name(r"CN=Doe\, Pat,OU=R\+D\, East,OU=Z\C5\82oty\20,DC=x")
        assert pairs == [
            ("cn", "Doe, Pat"),
            ("ou", "R+D, East"),
            ("ou", "Z\u0142oty "),
            ("dc", "x"),
        ]

    def test_an_escaped_leading_space_is_kept(self):
        assert groups.parse_distinguished_name(r"OU=\ Sales,DC=x")[0] == ("ou", " Sales")

    @pytest.mark.parametrize("value", [None, "", 5, "garbage", "CN="])
    def test_garbage_gives_no_pairs_with_a_value(self, value):
        assert all(not v for _, v in groups.parse_distinguished_name(value))


@pytest.mark.unit
class TestOrgUnitGroups:
    def test_the_ou_path_is_nested_from_the_top_and_the_person_is_in_the_innermost(self):
        result = groups.org_unit_groups(PL_SALES)

        assert result == [
            ExternalGroup("ou:ou=poland", "Organizational unit: Poland", None, member=False),
            ExternalGroup("ou:ou=sales,ou=poland", "Sales", "ou:ou=poland", member=True),
        ]

    def test_same_named_ous_under_different_parents_are_different_groups(self):
        other = groups.org_unit_groups("CN=Hans,OU=Sales,OU=Germany,DC=x")

        assert other[1].id == "ou:ou=sales,ou=germany"
        assert other[1].id != groups.org_unit_groups(PL_SALES)[1].id

    def test_the_id_is_case_insensitive_and_escaped(self):
        assert groups.org_unit_groups("OU=R\\, D,OU=PL")[-1].id == "ou:ou=r\\, d,ou=pl"
        assert groups.org_unit_groups("OU=SALES,OU=poland")[-1].id == groups.org_unit_groups(PL_SALES)[-1].id

    @pytest.mark.parametrize("dn", ["CN=Pat,CN=Users,DC=corp,DC=local", "CN=Pat,DC=corp", "", None, "OU=,DC=x", "   "])
    def test_no_ou_means_no_group(self, dn):
        assert groups.org_unit_groups(dn) == []

    def test_a_single_ou_is_one_top_level_member_group(self):
        assert groups.org_unit_groups("CN=Pat,OU=Sales,DC=x") == [
            ExternalGroup("ou:ou=sales", "Organizational unit: Sales", None, member=True)
        ]

    def test_depth_is_capped_below_the_deepest_a_group_can_nest(self):
        levels = [f"OU=L{n}" for n in range(15, 0, -1)]  # innermost first, outermost is L1
        result = groups.org_unit_groups(",".join(["CN=Pat", *levels, "DC=x"]))

        assert len(result) == groups.MAX_OU_LEVELS == MAX_GROUP_DEPTH - 1
        assert result[0].name == "Organizational unit: L1"
        assert result[-1].name == f"L{groups.MAX_OU_LEVELS}" and result[-1].member
        assert not any(g.member for g in result[:-1])

    def test_long_values_are_cut_and_ids_stay_within_the_column(self):
        levels = [f"OU={'x' * 300}{n}" for n in range(9, 0, -1)]
        result = groups.org_unit_groups(",".join(levels))

        assert all(len(g.id) <= 255 for g in result)
        assert len({g.id for g in result}) == len(result)
        assert all(len(g.name) <= 255 for g in result)


@pytest.mark.unit
class TestOfficeAndOrgUnitsFetch:
    def test_office_is_one_group_per_distinct_cleaned_value(self):
        result, graph = fetch({PROFILE_URL: {"officeLocation": "  Warsaw  HQ "}}, {groups.KIND_OFFICE})

        assert result == [ExternalGroup("office:warsaw hq", "Office: Warsaw HQ")]
        assert graph.calls[0][1] == {"$select": "officeLocation"}

    def test_org_units_are_nested_groups_and_one_profile_call_serves_every_kind(self):
        profile = {"department": "Sales", "officeLocation": "Warsaw", "onPremisesDistinguishedName": PL_SALES}
        kinds = {groups.KIND_DEPARTMENT, groups.KIND_OFFICE, groups.KIND_ORG_UNITS}

        result, graph = fetch({PROFILE_URL: profile}, kinds)

        assert len(graph.calls) == 1
        assert graph.calls[0][1] == {"$select": "department,officeLocation,onPremisesDistinguishedName"}
        assert {g.id for g in result} == {"department:sales", "office:warsaw", "ou:ou=poland", "ou:ou=sales,ou=poland"}

    def test_a_cloud_only_person_has_no_organizational_unit(self):
        result, _ = fetch({PROFILE_URL: {"onPremisesDistinguishedName": None}}, {groups.KIND_ORG_UNITS})

        assert result == []
