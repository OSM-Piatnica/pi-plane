# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Departments as groups: codes, order, the one-department rule and the sign-in sync."""

import pytest
from django.db import IntegrityError, transaction

from plane.authentication.provider.oidc.groups import ExternalGroup
from plane.db.models import GroupKind, GroupSource, User, UserGroup, UserGroupMember, Workspace, WorkspaceMember
from plane.utils.departments import (
    DepartmentError,
    check_one_department,
    code_taken,
    department_map,
    department_of,
    is_valid_color,
    next_sort_order,
    normalize_code,
)
from plane.utils.user_group_sync import sync_external_groups

IT = ExternalGroup(id="department:it", name="Department: IT")
HR = ExternalGroup(id="department:hr", name="Department: HR")


def _department(workspace, name, code="", **extra):
    return UserGroup.objects.create(workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT, **extra)


def _join(group, member, **extra):
    return UserGroupMember.objects.create(workspace=group.workspace, group=group, user=member.member, **extra)


def _in(group, member):
    return UserGroupMember.objects.filter(group=group, user=member.member).exists()


def _mirror(ws, member, *groups):
    """Sign in with these provider groups, then return the mirrored groups marked as departments."""
    sync_external_groups(member.member, GroupSource.ENTRA, list(groups))
    found = []
    for group in groups:
        mirrored = UserGroup.objects.get(workspace=ws, external_id=group.id)
        mirrored.kind = GroupKind.DEPARTMENT
        mirrored.save(update_fields=["kind"])
        found.append(mirrored)
    return found


@pytest.mark.unit
class TestPureHelpers:
    def test_codes_are_trimmed_and_upper_cased(self):
        assert normalize_code("  rm ") == "RM"
        assert normalize_code(None) == ""

    @pytest.mark.parametrize("value", ["", "#fff", "#3f76ff", "#3F76FFAA"])
    def test_hex_colours_are_accepted(self, value):
        assert is_valid_color(value)

    @pytest.mark.parametrize("value", ["red", "3f76ff", "#12", "#12345", "#gggggg", "rgb(0,0,0)"])
    def test_other_colours_are_refused(self, value):
        assert not is_valid_color(value)


@pytest.mark.unit
@pytest.mark.django_db
class TestDepartments:
    @pytest.fixture
    def ws(self, create_user):
        workspace = Workspace.objects.create(name="W", slug="w", owner=create_user)
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    @pytest.fixture
    def pat(self, ws):
        user = User.objects.create(email="pat@example.com", username="pat")
        return WorkspaceMember.objects.create(workspace=ws, member=user, role=15)

    def test_the_database_refuses_a_second_department_with_the_same_code(self, ws):
        _department(ws, "Marketing", "RM")
        # Plain groups and departments without a code are outside the rule
        UserGroup.objects.create(workspace=ws, name="Group one", code="RM")
        _department(ws, "No code one")
        _department(ws, "No code two")

        with pytest.raises(IntegrityError), transaction.atomic():
            _department(ws, "Other", "RM")
        assert code_taken(ws.id, "RM") and not code_taken(ws.id, "QA") and not code_taken(ws.id, "")

    def test_a_new_department_goes_after_the_last_one(self, ws):
        assert next_sort_order(ws.id) == 10000
        _department(ws, "Marketing", "RM", sort_order=25000)

        assert next_sort_order(ws.id) == 35000

    def test_my_department_is_the_active_department_group_i_belong_to(self, ws, pat):
        marketing = _department(ws, "Marketing", "RM")
        closed = _department(ws, "Closed", "CL", is_active=False)
        plain = UserGroup.objects.create(workspace=ws, name="Sales")
        below = UserGroup.objects.create(workspace=ws, name="Team", parent=marketing)
        for group in (closed, plain, below):
            _join(group, pat)
        # Neither a switched-off department, a plain group nor a group below a department counts
        assert department_of(ws.id, pat.member_id) is None

        _join(marketing, pat)

        assert department_of(ws.id, pat.member_id) == marketing
        assert department_map(ws.id) == {pat.member_id: marketing.id}

    def test_a_second_active_department_is_refused_with_the_names(self, ws, pat):
        marketing, quality = _department(ws, "Marketing", "RM"), _department(ws, "Quality", "QA")
        closed = _department(ws, "Closed", "CL", is_active=False)
        _join(marketing, pat)

        with pytest.raises(DepartmentError, match="Marketing") as raised:
            check_one_department(quality, [pat.member_id])
        # What the views answer with: the message and the people, set explicitly
        assert raised.value.detail == "A person belongs to at most one department. Already in another department: " + (
            f"{raised.value.people[0]}."
        )
        assert len(raised.value.people) == 1 and raised.value.people[0].endswith("(Marketing)")
        # The same department again, a switched-off one and a plain group are fine
        check_one_department(marketing, [pat.member_id])
        check_one_department(closed, [pat.member_id])
        check_one_department(UserGroup.objects.create(workspace=ws, name="Sales"), [pat.member_id])


@pytest.mark.unit
@pytest.mark.django_db
class TestDepartmentSync:
    """At sign-in the provider's first listed active department wins; see docs/departments.md."""

    @pytest.fixture
    def ws(self, create_user):
        workspace = Workspace.objects.create(name="W", slug="w", owner=create_user)
        WorkspaceMember.objects.create(workspace=workspace, member=create_user, role=20)
        return workspace

    @pytest.fixture
    def pat(self, ws):
        user = User.objects.create(email="pat@example.com", username="pat")
        return WorkspaceMember.objects.create(workspace=ws, member=user, role=15)

    def test_a_mirrored_group_marked_as_a_department_follows_the_provider(self, ws, pat):
        (it,) = _mirror(ws, pat, IT)
        assert department_of(ws.id, pat.member_id) == it

        # Moved to another department at the provider: the new one is theirs in the same sign-in
        sync_external_groups(pat.member, GroupSource.ENTRA, [HR])
        hr = UserGroup.objects.get(workspace=ws, external_id=HR.id)
        hr.kind = GroupKind.DEPARTMENT
        hr.save(update_fields=["kind"])
        sync_external_groups(pat.member, GroupSource.ENTRA, [HR])

        assert not _in(it, pat)
        assert department_of(ws.id, pat.member_id) == hr

    def test_of_two_departments_at_the_provider_the_first_listed_is_kept(self, ws, pat):
        it, hr = _mirror(ws, pat, IT, HR)
        # Marked as departments after the first sign-in: the next one settles it
        sync_external_groups(pat.member, GroupSource.ENTRA, [IT, HR])

        assert _in(it, pat) and not _in(hr, pat)

        sync_external_groups(pat.member, GroupSource.ENTRA, [HR, IT])

        assert _in(hr, pat) and not _in(it, pat)
        assert department_of(ws.id, pat.member_id) == hr

    def test_the_providers_department_replaces_one_made_by_hand(self, ws, pat):
        marketing = _department(ws, "Marketing", "RM")
        closed = _department(ws, "Closed", "CL", is_active=False)
        _join(marketing, pat)
        _join(closed, pat)

        (it,) = _mirror(ws, pat, IT)
        sync_external_groups(pat.member, GroupSource.ENTRA, [IT])

        assert not _in(marketing, pat)
        # A switched-off department is not a department of anybody, so it stays
        assert _in(closed, pat)
        assert department_of(ws.id, pat.member_id) == it

    def test_without_a_department_at_the_provider_the_hand_made_one_stays(self, ws, pat):
        marketing = _department(ws, "Marketing", "RM")
        _join(marketing, pat)

        sync_external_groups(pat.member, GroupSource.ENTRA, [IT])
        sync_external_groups(pat.member, GroupSource.ENTRA, [])

        assert department_of(ws.id, pat.member_id) == marketing
