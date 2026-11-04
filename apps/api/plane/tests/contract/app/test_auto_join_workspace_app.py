# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""People of the company's email domains join the chosen workspace when they sign in, also without an invite."""

import json
import uuid
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from plane.db.models import Profile, User, Workspace, WorkspaceMember, WorkspaceMemberInvite
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.settings.redis import redis_instance
from plane.utils.auto_join_workspace import (
    DOMAINS_KEY,
    ROLE_KEY,
    WORKSPACE_KEY,
    invalid_domains,
    join_auto_join_workspace,
    parse_domains,
)

STRONG_PASSWORD = "Xk9#mQ2$vL7@pR4!"
CONFIGURATIONS = "/api/instances/configurations/"


@pytest.fixture(autouse=True)
def clear_cache():
    """Instance settings and the auth throttle live in the cache, which the tests share."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Test",
        instance_id=uuid.uuid4().hex,
        current_version="1.0.0",
        domain="http://localhost:8000",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def company(workspace):
    """The settings, switched on for the workspace of the shared fixtures and the domain example.com."""
    for key, value in ((WORKSPACE_KEY, str(workspace.id)), (ROLE_KEY, "15"), (DOMAINS_KEY, "example.com")):
        InstanceConfiguration.objects.create(key=key, value=value, category="WORKSPACE_MANAGEMENT")
    return workspace


def set_setting(key, value):
    InstanceConfiguration.objects.filter(key=key).update(value=value)


def new_user(email, **fields):
    user = User.objects.create(email=email, username=uuid.uuid4().hex, **fields)
    Profile.objects.create(user=user)
    return user


def browser():
    """A client that sends a User-Agent, which signing in records."""
    return Client(HTTP_USER_AGENT="Mozilla/5.0")


def membership(workspace, user):
    return WorkspaceMember.objects.filter(workspace=workspace, member=user).first()


@pytest.mark.contract
@pytest.mark.django_db
class TestJoining:
    def test_a_person_of_the_domain_joins_as_member(self, company):
        user = new_user("anna@example.com")

        member = join_auto_join_workspace(user)

        assert member is not None
        assert member.role == 15 and member.is_active

    def test_landing_in_the_workspace_skips_the_create_step(self, company):
        user = new_user("anna@example.com")

        join_auto_join_workspace(user)

        profile = Profile.objects.get(user=user)
        assert profile.last_workspace_id == company.id
        assert profile.onboarding_step["workspace_join"] is True
        # The other steps are left as they were
        assert profile.onboarding_step["profile_complete"] is False

    def test_the_domain_matches_whatever_the_case(self, company):
        set_setting(DOMAINS_KEY, " @Example.COM , other.org")
        user = new_user("Anna@EXAMPLE.com")

        assert join_auto_join_workspace(user) is not None

    def test_another_domain_does_not_join(self, company):
        user = new_user("anna@example.org")

        assert join_auto_join_workspace(user) is None
        assert membership(company, user) is None

    def test_a_subdomain_is_not_the_domain(self, company):
        user = new_user("anna@mail.example.com")

        assert join_auto_join_workspace(user) is None

    def test_the_guest_role_is_used_when_chosen(self, company):
        set_setting(ROLE_KEY, "5")
        user = new_user("anna@example.com")

        assert join_auto_join_workspace(user).role == 5

    def test_an_invite_decides_the_role_and_is_used_up(self, company):
        WorkspaceMemberInvite.objects.create(workspace=company, email="anna@example.com", role=20)
        user = new_user("anna@example.com")

        assert join_auto_join_workspace(user).role == 20
        assert not WorkspaceMemberInvite.objects.filter(workspace=company, email="anna@example.com").exists()

    def test_a_suspended_member_is_not_added_again(self, company):
        user = new_user("anna@example.com")
        WorkspaceMember.objects.create(workspace=company, member=user, role=15, is_active=False)

        assert join_auto_join_workspace(user) is None
        assert WorkspaceMember.objects.filter(workspace=company, member=user).count() == 1
        assert membership(company, user).is_active is False

    def test_a_bot_does_not_join(self, company):
        user = new_user("bot@example.com", is_bot=True)

        assert join_auto_join_workspace(user) is None

    def test_a_deactivated_account_does_not_join(self, company):
        user = new_user("anna@example.com", is_active=False)

        assert join_auto_join_workspace(user) is None

    @pytest.mark.parametrize(
        "key, value",
        [(WORKSPACE_KEY, ""), (WORKSPACE_KEY, "not-a-uuid"), (DOMAINS_KEY, ""), (ROLE_KEY, "20")],
    )
    def test_nothing_happens_unless_fully_set_up(self, company, key, value):
        set_setting(key, value)
        user = new_user("anna@example.com")

        assert join_auto_join_workspace(user) is None

    def test_nothing_happens_without_the_settings(self, workspace):
        user = new_user("anna@example.com")

        assert join_auto_join_workspace(user) is None

    def test_a_deleted_workspace_turns_it_off(self, company):
        Workspace.objects.filter(id=company.id).delete()
        user = new_user("anna@example.com")

        assert join_auto_join_workspace(user) is None


@pytest.mark.contract
@pytest.mark.django_db
class TestSignIn:
    """The app's sign-in flows run the join; the public site (Space) does not."""

    @patch("plane.authentication.adapter.base.user_activation_email")
    def test_signing_up_with_a_password_joins(self, _mock_email, instance, company):
        browser().post(reverse("sign-up"), {"email": "anna@example.com", "password": STRONG_PASSWORD})

        user = User.objects.get(email="anna@example.com")
        assert membership(company, user).role == 15

    @patch("plane.authentication.adapter.base.user_activation_email")
    def test_signing_up_from_another_domain_does_not_join(self, _mock_email, instance, company):
        browser().post(reverse("sign-up"), {"email": "anna@example.org", "password": STRONG_PASSWORD})

        user = User.objects.get(email="anna@example.org")
        assert membership(company, user) is None

    @patch("plane.bgtasks.one_time_code_task.send_one_time_code.delay")
    def test_signing_up_with_a_code_joins(self, _mock_send, instance, company, api_client):
        email = "anna@example.com"
        api_client.post(reverse("magic-generate"), {"email": email}, format="json")
        token = json.loads(redis_instance().get(f"one_time_code_{email}"))["token"]

        browser().post(reverse("magic-sign-up"), {"email": email, "code": token})

        assert membership(company, User.objects.get(email=email)) is not None

    def test_signing_in_later_joins_an_existing_account(self, instance, company):
        user = new_user("anna@example.com")
        user.set_password(STRONG_PASSWORD)
        user.save()

        browser().post(reverse("sign-in"), {"email": "anna@example.com", "password": STRONG_PASSWORD})

        assert membership(company, user) is not None

    @patch("plane.authentication.adapter.base.user_activation_email")
    def test_signing_up_on_the_public_site_does_not_join(self, _mock_email, instance, company):
        browser().post(reverse("space-sign-up"), {"email": "anna@example.com", "password": STRONG_PASSWORD})

        user = User.objects.get(email="anna@example.com")
        assert membership(company, user) is None


@pytest.fixture
def instance_admin(instance, create_user):
    return InstanceAdmin.objects.create(instance=instance, user=create_user, role=20)


@pytest.mark.contract
@pytest.mark.django_db
class TestSettings:
    def test_an_instance_admin_can_set_it_up(self, session_client, instance_admin, company):
        set_setting(WORKSPACE_KEY, "")
        response = session_client.patch(
            CONFIGURATIONS,
            {WORKSPACE_KEY: str(company.id), ROLE_KEY: "5", DOMAINS_KEY: "example.com, example.org"},
            format="json",
        )

        assert response.status_code == 200, response.data
        values = dict(InstanceConfiguration.objects.filter(key__startswith="AUTO_JOIN_").values_list("key", "value"))
        assert values == {WORKSPACE_KEY: str(company.id), ROLE_KEY: "5", DOMAINS_KEY: "example.com, example.org"}

    def test_it_can_be_turned_off(self, session_client, instance_admin, company):
        response = session_client.patch(CONFIGURATIONS, {WORKSPACE_KEY: ""}, format="json")

        assert response.status_code == 200, response.data
        assert InstanceConfiguration.objects.get(key=WORKSPACE_KEY).value == ""

    @pytest.mark.parametrize("value", [str(uuid.uuid4()), "not-a-workspace"])
    def test_an_unknown_workspace_is_refused(self, session_client, instance_admin, company, value):
        response = session_client.patch(CONFIGURATIONS, {WORKSPACE_KEY: value}, format="json")

        assert response.status_code == 400
        assert InstanceConfiguration.objects.get(key=WORKSPACE_KEY).value == str(company.id)

    @pytest.mark.parametrize("value", ["20", "admin", "0"])
    def test_only_member_or_guest_is_accepted(self, session_client, instance_admin, company, value):
        response = session_client.patch(CONFIGURATIONS, {ROLE_KEY: value}, format="json")

        assert response.status_code == 400
        assert InstanceConfiguration.objects.get(key=ROLE_KEY).value == "15"

    def test_a_wrong_domain_is_refused(self, session_client, instance_admin, company):
        response = session_client.patch(CONFIGURATIONS, {DOMAINS_KEY: "example.com, not a domain"}, format="json")

        assert response.status_code == 400
        assert "not a domain" in response.data["error"]
        assert InstanceConfiguration.objects.get(key=DOMAINS_KEY).value == "example.com"


@pytest.mark.unit
def test_domains_are_read_loosely_and_checked_strictly():
    assert parse_domains(" @Example.com,, piatnica.com.pl ") == ["example.com", "piatnica.com.pl"]
    assert invalid_domains("example.com, @sub.example.co.uk") == []
    assert invalid_domains("example, exa mple.com, -bad.com, example.com/") == [
        "example",
        "exa mple.com",
        "-bad.com",
        "example.com/",
    ]


@pytest.mark.contract
@pytest.mark.django_db
class TestCommand:
    def test_dry_run_lists_without_joining(self, company):
        anna = new_user("anna@example.com")
        new_user("bob@example.org")

        out = StringIO()
        call_command("join_default_workspace", "--dry-run", stdout=out)

        assert "Would join: anna@example.com" in out.getvalue()
        assert "bob@example.org" not in out.getvalue()
        assert membership(company, anna) is None

    def test_it_joins_existing_accounts(self, company):
        anna = new_user("anna@example.com")
        suspended = new_user("eve@example.com")
        WorkspaceMember.objects.create(workspace=company, member=suspended, role=15, is_active=False)

        out = StringIO()
        call_command("join_default_workspace", stdout=out)

        assert membership(company, anna).is_active
        assert membership(company, suspended).is_active is False
        assert "1 account(s) joined" in out.getvalue()

    def test_it_refuses_when_not_set_up(self, workspace):
        with pytest.raises(CommandError):
            call_command("join_default_workspace")
