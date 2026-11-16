# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The department of a workspace member and the group membership that goes with it."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from plane.authentication.provider.oidc.groups import ExternalGroup
from plane.db.models import GroupKind, GroupSource, User, UserGroup, UserGroupMember, Workspace, WorkspaceMember
from plane.utils.departments import (
    DepartmentError,
    adopt_department,
    code_taken,
    is_valid_color,
    next_sort_order,
    normalize_code,
    set_department,
)
from plane.utils.user_group_sync import sync_external_groups

IT = ExternalGroup(id="department:it", name="Department: IT")
HR = ExternalGroup(id="department:hr", name="Department: HR")


def _department(workspace, name, code="", **extra):
    return UserGroup.objects.create(workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT, **extra)


def _fresh(member):
    return WorkspaceMember.objects.get(pk=member.pk)


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

    def test_setting_a_department_keeps_the_group_membership_in_step(self, ws, pat):
        marketing, quality = _department(ws, "Marketing", "RM"), _department(ws, "Quality", "QA")

        set_department(pat, marketing)
        set_department(pat, quality)

        assert _fresh(pat).department_id == quality.id
        groups = set(UserGroupMember.objects.filter(user=pat.member).values_list("group_id", flat=True))
        assert groups == {quality.id}

        set_department(pat, None)

        assert _fresh(pat).department_id is None
        assert not UserGroupMember.objects.filter(user=pat.member).exists()

    def test_a_membership_made_before_is_reused(self, ws, pat):
        marketing = _department(ws, "Marketing", "RM")
        UserGroupMember.objects.create(workspace=ws, group=marketing, user=pat.member)

        set_department(pat, marketing)

        assert UserGroupMember.objects.filter(group=marketing, user=pat.member).count() == 1

    def test_what_is_not_an_active_department_of_the_workspace_is_refused(self, ws, pat, create_user):
        other = Workspace.objects.create(name="O", slug="o", owner=create_user)
        candidates = [
            UserGroup.objects.create(workspace=ws, name="Sales"),
            _department(ws, "Closed", "CL", is_active=False),
            _department(other, "Foreign", "FR"),
            _department(ws, "Mirrored", "MI", source=GroupSource.ENTRA, external_id="department:mi"),
        ]

        for group in candidates:
            with pytest.raises(DepartmentError):
                set_department(pat, group)
        assert _fresh(pat).department_id is None

    def test_the_model_refuses_a_department_written_around_the_helper(self, ws, pat, create_user):
        other = Workspace.objects.create(name="O", slug="o", owner=create_user)
        plain = UserGroup.objects.create(workspace=ws, name="Sales")

        for group in (plain, _department(other, "Foreign", "FR")):
            pat.department = group
            with pytest.raises(ValidationError):
                pat.save()
            with pytest.raises(ValidationError):
                pat.save(update_fields=["department"])
        assert _fresh(pat).department_id is None

    def test_adopting_never_replaces_a_department(self, ws, pat):
        marketing, quality = _department(ws, "Marketing", "RM"), _department(ws, "Quality", "QA")
        plain = UserGroup.objects.create(workspace=ws, name="Sales")

        adopt_department(ws.id, pat.member_id, plain)
        assert _fresh(pat).department_id is None
        adopt_department(ws.id, pat.member_id, marketing)
        adopt_department(ws.id, pat.member_id, quality)

        assert _fresh(pat).department_id == marketing.id

    def test_a_mirrored_group_marked_as_a_department_follows_the_provider(self, ws, pat):
        # The first sign-in mirrors the group; nothing is a department until a workspace admin says so
        sync_external_groups(pat.member, GroupSource.ENTRA, [IT])
        mirrored = UserGroup.objects.get(workspace=ws, external_id="department:it")
        assert mirrored.kind == GroupKind.GROUP and _fresh(pat).department_id is None

        mirrored.kind = GroupKind.DEPARTMENT
        mirrored.save(update_fields=["kind"])
        sync_external_groups(pat.member, GroupSource.ENTRA, [IT])

        assert _fresh(pat).department_id == mirrored.id

        # Moved to another department at the provider: the old one is no longer theirs
        sync_external_groups(pat.member, GroupSource.ENTRA, [HR])

        assert _fresh(pat).department_id is None
        assert not UserGroupMember.objects.filter(group=mirrored, user=pat.member).exists()

    def test_the_sync_leaves_a_department_chosen_by_hand_alone(self, ws, pat):
        marketing = _department(ws, "Marketing", "RM")
        set_department(pat, marketing)

        sync_external_groups(pat.member, GroupSource.ENTRA, [IT])
        sync_external_groups(pat.member, GroupSource.ENTRA, [])

        assert _fresh(pat).department_id == marketing.id
        assert UserGroupMember.objects.filter(group=marketing, user=pat.member).exists()
