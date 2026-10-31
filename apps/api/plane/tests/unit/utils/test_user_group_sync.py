# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The mirror of a person's provider groups, in particular groups nested under each other (organizational units)."""

import pytest

from plane.authentication.provider.oidc.groups import ExternalGroup, org_unit_groups
from plane.db.models import Account, GroupSource, User, UserGroup, UserGroupMember, Workspace, WorkspaceMember
from plane.utils.user_group_sync import sync_external_groups
from plane.utils.user_groups import MAX_GROUP_DEPTH, depth_of, group_ids_of_user, member_user_ids

PL_SALES = "CN=Pat,OU=Sales,OU=Poland,DC=corp,DC=local"
PL_HR = "CN=Ola,OU=HR,OU=Poland,DC=corp,DC=local"
DE_SALES = "CN=Hans,OU=Sales,OU=Germany,DC=corp,DC=local"


def _person(name):
    user = User.objects.create(email=f"{name}@example.com", username=name)
    return user


def _join(workspace, user):
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)


def _sync(user, dn):
    sync_external_groups(user, GroupSource.ENTRA, org_unit_groups(dn))


def _tree(workspace):
    """name path of every Entra group, e.g. 'Organizational unit: Poland/Sales'."""
    groups = {group.id: group for group in UserGroup.objects.filter(workspace=workspace, source=GroupSource.ENTRA)}

    def path(group):
        return path(groups[group.parent_id]) + "/" + group.name if group.parent_id else group.name

    return {path(group) for group in groups.values()}


def _member_of(user, workspace):
    return set(
        UserGroupMember.objects.filter(workspace=workspace, user=user).values_list("group__external_id", flat=True)
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestNestedGroups:
    @pytest.fixture
    def ws(self, create_user):
        workspace = Workspace.objects.create(name="W", slug="w", owner=create_user)
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    def test_the_parent_chain_is_built_and_only_the_innermost_has_the_person(self, ws):
        pat = _person("pat")
        _join(ws, pat)

        _sync(pat, PL_SALES)

        assert _tree(ws) == {"Organizational unit: Poland", "Organizational unit: Poland/Sales"}
        assert _member_of(pat, ws) == {"ou:ou=sales,ou=poland"}
        parent = UserGroup.objects.get(external_id="ou:ou=poland")
        assert parent.parent_id is None and not UserGroupMember.objects.filter(group=parent).exists()
        # belonging to the parent follows from the nesting
        assert pat.id in member_user_ids(ws.id, [parent.id])
        assert parent.id in group_ids_of_user(ws.id, pat.id)

    def test_a_second_person_in_a_sibling_ou_shares_the_parent(self, ws):
        pat, ola = _person("pat"), _person("ola")
        _join(ws, pat)
        _join(ws, ola)

        _sync(pat, PL_SALES)
        _sync(ola, PL_HR)

        assert UserGroup.objects.filter(external_id="ou:ou=poland").count() == 1
        assert _tree(ws) == {
            "Organizational unit: Poland",
            "Organizational unit: Poland/Sales",
            "Organizational unit: Poland/HR",
        }
        parent = UserGroup.objects.get(external_id="ou:ou=poland")
        assert member_user_ids(ws.id, [parent.id]) == {pat.id, ola.id}

    def test_same_named_ous_under_different_parents_stay_distinct(self, ws):
        pat, hans = _person("pat"), _person("hans")
        _join(ws, pat)
        _join(ws, hans)

        _sync(pat, PL_SALES)
        _sync(hans, DE_SALES)

        sales = UserGroup.objects.filter(name="Sales")
        assert sales.count() == 2 and len({group.parent_id for group in sales}) == 2
        assert _member_of(pat, ws) == {"ou:ou=sales,ou=poland"}
        assert _member_of(hans, ws) == {"ou:ou=sales,ou=germany"}

    def test_an_ou_change_moves_the_person_and_leaves_the_empty_groups_in_place(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        _sync(pat, PL_SALES)

        _sync(pat, PL_HR)

        assert _member_of(pat, ws) == {"ou:ou=hr,ou=poland"}
        assert UserGroup.objects.filter(external_id="ou:ou=sales,ou=poland", deleted_at__isnull=True).exists()
        assert not UserGroupMember.objects.filter(group__external_id="ou:ou=sales,ou=poland").exists()

        _sync(pat, DE_SALES)
        assert _member_of(pat, ws) == {"ou:ou=sales,ou=germany"}
        assert UserGroup.objects.filter(external_id="ou:ou=hr,ou=poland").exists()

    def test_no_ou_takes_the_person_out_and_deletes_nothing(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        _sync(pat, PL_SALES)
        before = UserGroup.objects.count()

        _sync(pat, "CN=Pat,CN=Users,DC=corp,DC=local")

        assert _member_of(pat, ws) == set()
        assert UserGroup.objects.count() == before

    def test_a_top_level_name_that_is_taken_is_clarified(self, ws):
        UserGroup.objects.create(workspace=ws, name="Organizational unit: Poland")
        pat = _person("pat")
        _join(ws, pat)

        _sync(pat, PL_SALES)

        assert UserGroup.objects.get(external_id="ou:ou=poland").name == "Organizational unit: Poland (Entra)"

    def test_a_name_taken_among_siblings_is_clarified_under_the_parent_only(self, ws):
        parent = UserGroup.objects.create(workspace=ws, name="Elsewhere")
        UserGroup.objects.create(workspace=ws, name="Sales", parent=parent)
        pat = _person("pat")
        _join(ws, pat)

        # "Sales" exists under another parent: no clash under Poland
        _sync(pat, PL_SALES)

        assert UserGroup.objects.get(external_id="ou:ou=sales,ou=poland").name == "Sales"

    def test_a_group_that_was_moved_by_hand_is_put_back_under_the_providers_parent(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        _sync(pat, PL_SALES)
        sales = UserGroup.objects.get(external_id="ou:ou=sales,ou=poland")
        sales.parent = None
        sales.name = "Sales moved"
        sales.save()

        _sync(pat, PL_SALES)

        sales.refresh_from_db()
        assert sales.parent.external_id == "ou:ou=poland" and sales.name == "Sales"

    def test_a_flat_group_is_never_moved(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        sync_external_groups(pat, GroupSource.ENTRA, [ExternalGroup("g1", "Sales")])
        flat = UserGroup.objects.get(external_id="g1")
        home = UserGroup.objects.create(workspace=ws, name="Home")
        flat.parent = home
        flat.save()

        sync_external_groups(pat, GroupSource.ENTRA, [ExternalGroup("g1", "Sales")])

        flat.refresh_from_db()
        assert flat.parent_id == home.id

    def test_the_deepest_tree_still_fits_the_nesting_limit(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        dn = ",".join(["CN=Pat", *[f"OU=L{n}" for n in range(15, 0, -1)], "DC=x"])

        _sync(pat, dn)

        member = UserGroupMember.objects.get(user=pat)
        assert depth_of(ws.id, member.group_id) == MAX_GROUP_DEPTH - 1
        assert UserGroup.objects.filter(source=GroupSource.ENTRA).count() == MAX_GROUP_DEPTH - 1

    def test_a_chain_deeper_than_the_limit_is_not_created(self, ws):
        pat = _person("pat")
        _join(ws, pat)
        chain = [ExternalGroup(f"n{n}", f"N{n}", f"n{n - 1}" if n else None, member=n == 11) for n in range(12)]

        sync_external_groups(pat, GroupSource.ENTRA, chain)

        assert UserGroup.objects.filter(external_id="n9").exists()
        assert not UserGroup.objects.filter(external_id="n10").exists()
        assert not UserGroup.objects.filter(external_id="n11").exists()
        assert not UserGroupMember.objects.filter(user=pat).exists()

    def test_a_workspace_joined_later_gets_the_stored_tree(self, ws, create_user):
        pat = _person("pat")
        Account.objects.create(user=pat, provider="entra", provider_account_id="x")
        _join(ws, pat)  # a first workspace, so that the sync has somewhere to go
        _sync(pat, PL_SALES)
        other = Workspace.objects.create(name="O", slug="o", owner=create_user)

        _join(other, pat)

        assert _tree(other) == {"Organizational unit: Poland", "Organizational unit: Poland/Sales"}
        assert _member_of(pat, other) == {"ou:ou=sales,ou=poland"}
