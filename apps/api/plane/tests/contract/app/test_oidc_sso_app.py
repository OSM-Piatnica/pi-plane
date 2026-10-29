# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Single sign-on through OpenID Connect, against a fake identity provider."""

import json
import time
import uuid
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES
from plane.authentication.provider.oidc import client as oidc_client
from plane.authentication.provider.oidc.registry import enabled_oidc_providers, oidc_config_variables
from plane.db.models import (
    Account,
    GroupRole,
    GroupSource,
    User,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceMember,
)
from plane.license.models import Instance

TENANT = "11111111-2222-3333-4444-555555555555"
OID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
CLIENT_ID = "client-id"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks(key=KEY):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    return {"keys": [{**jwk, "kid": "kid-1", "use": "sig", "alg": "RS256"}]}


class FakeResponse:
    def __init__(self, payload, status=200, raw=None):
        self.payload, self.status_code = payload, status
        self.raw = raw if raw is not None else json.dumps(payload).encode()

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.raw), chunk_size):
            yield self.raw[i : i + chunk_size]

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload

    def close(self):
        pass


class FakeIdp:
    """Serves the discovery document and the keys, and answers the code exchange with the prepared ID token."""

    def __init__(self, issuer=ISSUER):
        self.issuer = issuer
        self.id_token = None
        self.exchanged = []
        self.token_status = 200
        self.token_payload = None
        self.oversized_keys = False
        # url prefix -> handler(url, kwargs) returning the JSON the provider's API answers with
        self.api = {}
        self.api_calls = []

    def fetch(self, method, url, **kwargs):
        if url.endswith("/.well-known/openid-configuration"):
            return FakeResponse(
                {
                    "issuer": self.issuer,
                    "authorization_endpoint": "https://idp.example.com/authorize",
                    "token_endpoint": "https://idp.example.com/token",
                    "jwks_uri": "https://idp.example.com/keys",
                }
            )
        if url == "https://idp.example.com/keys":
            if self.oversized_keys:
                return FakeResponse(None, raw=b" " * (2 * 1024 * 1024))
            return FakeResponse(_jwks())
        if url == "https://idp.example.com/token":
            self.exchanged.append(kwargs["data"])
            if self.token_status != 200:
                return FakeResponse(self.token_payload, status=self.token_status)
            return FakeResponse({"id_token": self.id_token, "access_token": "secret-access", "refresh_token": "r"})
        for prefix, handler in self.api.items():
            if url.startswith(prefix):
                self.api_calls.append((method, url, kwargs))
                return FakeResponse(handler(url, kwargs))
        raise AssertionError(f"unexpected fetch {url}")


def make_token(nonce, /, key=KEY, **overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "pairwise-sub",
        "tid": TENANT,
        "oid": OID,
        "iat": now,
        "exp": now + 600,
        "nonce": nonce,
        "email": "Ala.Kowalska@piatnica.com.pl",
        "name": "Ala Kowalska",
    }
    claims.update(overrides)
    return jwt.encode(
        {k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256", headers={"kid": "kid-1"}
    )


CONFIG = {}


def _config(keys):
    return tuple(CONFIG.get(k["key"], k.get("default")) for k in keys)


@pytest.fixture(autouse=True)
def _env():
    CONFIG.clear()
    CONFIG.update(
        {
            "IS_ENTRA_ENABLED": "1",
            "ENTRA_CLIENT_ID": CLIENT_ID,
            "ENTRA_CLIENT_SECRET": "client-secret",
            "ENTRA_TENANT_ID": TENANT,
        }
    )
    cache.delete_pattern("oidc:*")
    with patch("plane.license.utils.instance_value.get_configuration_value", side_effect=_config):
        yield
    cache.delete_pattern("oidc:*")


@pytest.fixture
def idp():
    fake = FakeIdp()
    with patch("plane.authentication.provider.oidc.client.pinned_fetch", side_effect=fake.fetch):
        yield fake


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Test Instance",
        instance_id=str(uuid.uuid4()),
        current_version="1.0.0",
        domain="http://localhost:8000",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


def sign_in(idp, provider="entra", surface="auth", token_kwargs=None, token=None, client=None):
    """Starts the sign-in and comes back from the provider; returns (client, callback response, authorize query)."""
    client = client or Client(HTTP_USER_AGENT="Mozilla/5.0")
    prefix = "space-oidc-initiate" if surface == "space" else "oidc-initiate"
    start = client.get(reverse(prefix, args=[provider]))
    assert start.status_code == 302 and start.url.startswith("https://idp.example.com/authorize"), start.url
    query = {k: v[0] for k, v in parse_qs(urlparse(start.url).query).items()}
    idp.id_token = token or make_token(query["nonce"], **(token_kwargs or {}))
    response = client.get(reverse("oidc-callback", args=[provider]), {"code": "the-code", "state": query["state"]})
    return client, response, query


def failed_with(response, code):
    assert response.status_code == 302
    return f"error_code={AUTHENTICATION_ERROR_CODES[code]}" in response.url


@pytest.mark.contract
@pytest.mark.django_db
class TestEntraSignIn:
    def test_initiation_sends_state_nonce_and_pkce(self, instance, idp):
        client = Client()
        start = client.get(reverse("oidc-initiate", args=["entra"]))
        query = parse_qs(urlparse(start.url).query)
        assert query["client_id"] == [CLIENT_ID]
        assert query["response_type"] == ["code"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["scope"] == ["openid profile email"]
        assert query["redirect_uri"][0].endswith("/auth/oidc/entra/callback/")
        assert query["state"][0] == client.session["state"]
        assert query["nonce"][0] == client.session["oidc_nonce"]

    def test_signs_up_a_new_person_and_binds_the_identity(self, instance, idp):
        client, response, query = sign_in(idp)

        assert "error_code" not in response.url
        user = User.objects.get(email="ala.kowalska@piatnica.com.pl")
        assert client.session["_auth_user_id"] == str(user.id)
        assert user.first_name == "Ala" and user.last_name == "Kowalska"
        account = Account.objects.get(user=user, provider="entra")
        assert account.provider_account_id == f"{TENANT}:{OID}"
        # No token of the provider is kept
        assert account.access_token == "" and not account.refresh_token and not account.id_token
        # The code exchange proves the possession of the PKCE verifier
        assert idp.exchanged[0]["code_verifier"]
        assert idp.exchanged[0]["code"] == "the-code"

    def test_second_sign_in_reuses_the_user(self, instance, idp):
        sign_in(idp)
        sign_in(idp)
        assert User.objects.filter(email="ala.kowalska@piatnica.com.pl").count() == 1
        assert Account.objects.filter(provider="entra").count() == 1

    def test_email_change_at_the_provider_keeps_the_same_user(self, instance, idp):
        sign_in(idp)
        user = User.objects.get(email="ala.kowalska@piatnica.com.pl")
        client, response, _ = sign_in(idp, token_kwargs={"email": "ala.nowak@piatnica.com.pl"})
        assert "error_code" not in response.url
        assert client.session["_auth_user_id"] == str(user.id)
        assert not User.objects.filter(email="ala.nowak@piatnica.com.pl").exists()

    def test_existing_user_is_bound_on_first_sign_in(self, instance, idp, create_user):
        CONFIG["ENTRA_LINK_EXISTING_ACCOUNTS"] = "1"
        client, response, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert "error_code" not in response.url
        assert client.session["_auth_user_id"] == str(create_user.id)
        assert Account.objects.get(user=create_user, provider="entra").provider_account_id == f"{TENANT}:{OID}"

    def test_account_bound_to_another_identity_is_not_taken_over_by_email(self, instance, idp, create_user):
        Account.objects.create(
            user=create_user, provider="entra", provider_account_id=f"{TENANT}:other-oid", access_token=""
        )
        client, response, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert failed_with(response, "OIDC_IDENTITY_MISMATCH")
        assert "_auth_user_id" not in client.session

    def test_falls_back_to_the_user_principal_name_without_email(self, instance, idp):
        _, response, _ = sign_in(idp, token_kwargs={"email": None, "preferred_username": "jan@piatnica.com.pl"})
        assert "error_code" not in response.url
        assert User.objects.filter(email="jan@piatnica.com.pl").exists()

    @pytest.mark.parametrize(
        "token_kwargs",
        [
            {"tid": "99999999-2222-3333-4444-555555555555"},
            {"oid": None},
            {"aud": "someone-else"},
            {"iss": "https://login.microsoftonline.com/other/v2.0"},
            {"exp": int(time.time()) - 3600},
            {"nonce": "not-the-nonce"},
            {"email": None, "preferred_username": None},
        ],
        ids=["other-tenant", "no-oid", "other-audience", "other-issuer", "expired", "wrong-nonce", "no-email"],
    )
    def test_refuses_a_token_that_is_not_ours(self, instance, idp, token_kwargs):
        client, response, _ = sign_in(idp, token_kwargs=token_kwargs)
        assert response.status_code == 302 and "error_code" in response.url
        assert "_auth_user_id" not in client.session
        assert not User.objects.filter(email__endswith="piatnica.com.pl").exists()

    def test_refuses_a_token_signed_with_another_key(self, instance, idp):
        client = Client()
        start = client.get(reverse("oidc-initiate", args=["entra"]))
        nonce = parse_qs(urlparse(start.url).query)["nonce"][0]
        _, response, _ = sign_in(idp, token=make_token(nonce, key=OTHER_KEY), client=client)
        # (the second initiation replaces the nonce, so this fails for two reasons: both are refusals)
        assert failed_with(response, "OIDC_PROVIDER_ERROR")

    def test_refuses_an_unsigned_token(self, instance, idp):
        client = Client()
        start = client.get(reverse("oidc-initiate", args=["entra"]))
        nonce = parse_qs(urlparse(start.url).query)["nonce"][0]
        unsigned = jwt.encode(
            {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "x",
                "tid": TENANT,
                "oid": OID,
                "iat": 1,
                "exp": 4102444800,
                "nonce": nonce,
            },
            None,
            algorithm="none",
        )
        idp.id_token = unsigned
        response = client.get(
            reverse("oidc-callback", args=["entra"]),
            {"code": "c", "state": parse_qs(urlparse(start.url).query)["state"][0]},
        )
        assert failed_with(response, "OIDC_PROVIDER_ERROR")
        assert "_auth_user_id" not in client.session

    def test_callback_cannot_be_replayed(self, instance, idp):
        client, response, query = sign_in(idp)
        replay = client.get(reverse("oidc-callback", args=["entra"]), {"code": "the-code", "state": query["state"]})
        assert failed_with(replay, "OIDC_PROVIDER_ERROR")

    def test_callback_without_a_started_sign_in_is_refused(self, instance, idp):
        response = Client().get(reverse("oidc-callback", args=["entra"]), {"code": "c", "state": "s"})
        assert failed_with(response, "OIDC_PROVIDER_ERROR")

    def test_provider_error_is_refused(self, instance, idp):
        client = Client()
        start = client.get(reverse("oidc-initiate", args=["entra"]))
        state = parse_qs(urlparse(start.url).query)["state"][0]
        response = client.get(reverse("oidc-callback", args=["entra"]), {"error": "access_denied", "state": state})
        assert failed_with(response, "OIDC_PROVIDER_ERROR")

    def test_discovery_of_another_issuer_is_refused(self, instance):
        fake = FakeIdp(issuer="https://evil.example.com/")
        with patch("plane.authentication.provider.oidc.client.pinned_fetch", side_effect=fake.fetch):
            response = Client().get(reverse("oidc-initiate", args=["entra"]))
        assert failed_with(response, "OIDC_PROVIDER_ERROR")

    def test_allowed_email_domains(self, instance, idp):
        CONFIG["ENTRA_ALLOWED_EMAIL_DOMAINS"] = "piatnica.com.pl, @example.org"
        _, ok, _ = sign_in(idp)
        assert "error_code" not in ok.url
        _, refused, _ = sign_in(idp, token_kwargs={"email": "intruder@gmail.com", "oid": str(uuid.uuid4())})
        assert failed_with(refused, "OIDC_EMAIL_DOMAIN_NOT_ALLOWED")
        assert not User.objects.filter(email="intruder@gmail.com").exists()

    def test_signup_can_be_disabled_per_provider(self, instance, idp, create_user):
        CONFIG["ENTRA_ENABLE_SIGNUP"] = "0"
        CONFIG["ENTRA_LINK_EXISTING_ACCOUNTS"] = "1"
        _, refused, _ = sign_in(idp)
        assert failed_with(refused, "SIGNUP_DISABLED")
        # people who already have an account still sign in
        client, ok, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert "error_code" not in ok.url
        assert client.session["_auth_user_id"] == str(create_user.id)

    def test_provider_signup_does_not_depend_on_the_email_signup_setting(self, instance, idp):
        CONFIG["ENABLE_SIGNUP"] = "0"
        _, response, _ = sign_in(idp)
        assert "error_code" not in response.url

    def test_deactivated_users_are_still_refused(self, instance, idp, create_user):
        CONFIG["ENTRA_LINK_EXISTING_ACCOUNTS"] = "1"
        create_user.is_active = False
        create_user.last_logout_time = timezone.now()
        create_user.save()
        _, response, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert failed_with(response, "USER_ACCOUNT_DEACTIVATED")

    def test_space_sign_in_returns_to_the_spaces(self, instance, idp):
        client, response, _ = sign_in(idp, surface="space")
        assert "error_code" not in response.url
        assert "_auth_user_id" in client.session
        assert "/spaces" in response.url


@pytest.mark.contract
@pytest.mark.django_db
class TestProviderAvailability:
    def test_not_configured_provider_is_refused(self, instance, idp):
        CONFIG.pop("ENTRA_CLIENT_SECRET")
        assert failed_with(Client().get(reverse("oidc-initiate", args=["entra"])), "OIDC_NOT_CONFIGURED")

    @pytest.mark.parametrize("tenant", ["common", "organizations", "piatnica.onmicrosoft.com", ""])
    def test_tenant_must_be_a_guid(self, instance, idp, tenant):
        CONFIG["ENTRA_TENANT_ID"] = tenant
        assert failed_with(Client().get(reverse("oidc-initiate", args=["entra"])), "OIDC_NOT_CONFIGURED")
        assert enabled_oidc_providers() == []

    def test_unknown_provider_is_refused(self, instance, idp):
        assert failed_with(Client().get(reverse("oidc-initiate", args=["nope"])), "OIDC_NOT_CONFIGURED")

    def test_public_list_has_only_enabled_and_configured_providers(self, db):
        assert enabled_oidc_providers() == [{"key": "entra", "name": "Microsoft", "icon": "microsoft"}]
        CONFIG["IS_ENTRA_ENABLED"] = "0"
        assert enabled_oidc_providers() == []

    def test_settings_of_every_provider_are_registered(self):
        keys = {v["key"] for v in oidc_config_variables()}
        assert {"IS_ENTRA_ENABLED", "ENTRA_CLIENT_ID", "ENTRA_CLIENT_SECRET", "ENTRA_TENANT_ID"} <= keys
        assert {"IS_OIDC_ENABLED", "OIDC_ISSUER_URL", "OIDC_CLIENT_SECRET"} <= keys
        secrets_ = {v["key"] for v in oidc_config_variables() if v.get("is_encrypted")}
        assert {"ENTRA_CLIENT_SECRET", "OIDC_CLIENT_SECRET"} <= secrets_


@pytest.mark.contract
@pytest.mark.django_db
class TestGenericOidc:
    @pytest.fixture(autouse=True)
    def _generic(self):
        CONFIG.update(
            {
                "IS_OIDC_ENABLED": "1",
                "OIDC_CLIENT_ID": CLIENT_ID,
                "OIDC_CLIENT_SECRET": "s",
                "OIDC_ISSUER_URL": ISSUER,
                "OIDC_DISPLAY_NAME": "Keycloak",
            }
        )

    def test_button_uses_the_configured_name(self):
        assert {"key": "oidc", "name": "Keycloak", "icon": "key"} in enabled_oidc_providers()

    def test_signs_in_with_a_verified_email(self, instance, idp):
        _, response, _ = sign_in(idp, provider="oidc", token_kwargs={"email_verified": True, "tid": None, "oid": None})
        assert "error_code" not in response.url
        assert Account.objects.get(provider="oidc").provider_account_id == f"{ISSUER}|pairwise-sub"

    @pytest.mark.parametrize("verified", [False, None])
    def test_refuses_an_unverified_email(self, instance, idp, verified):
        _, response, _ = sign_in(idp, provider="oidc", token_kwargs={"email_verified": verified})
        assert failed_with(response, "OAUTH_PROVIDER_UNVERIFIED_EMAIL")


@pytest.mark.contract
@pytest.mark.django_db
class TestGoogleOidc:
    @pytest.fixture(autouse=True)
    def _google(self):
        CONFIG.update(
            {"IS_GOOGLE_OIDC_ENABLED": "1", "GOOGLE_OIDC_CLIENT_ID": CLIENT_ID, "GOOGLE_OIDC_CLIENT_SECRET": "s"}
        )

    @pytest.fixture
    def google_idp(self):
        fake = FakeIdp(issuer="https://accounts.google.com")
        with patch("plane.authentication.provider.oidc.client.pinned_fetch", side_effect=fake.fetch):
            yield fake

    def sign_in(self, idp, **claims):
        claims = {"iss": "https://accounts.google.com", "email_verified": True, "tid": None, "oid": None, **claims}
        return sign_in(idp, provider="google-oidc", token_kwargs=claims)

    def test_button(self):
        assert {"key": "google-oidc", "name": "Google", "icon": "google"} in enabled_oidc_providers()

    def test_signs_in_and_binds_the_google_account_id(self, instance, google_idp):
        _, response, query = self.sign_in(google_idp)
        assert "error_code" not in response.url
        assert query["redirect_uri"].endswith("/auth/oidc/google-oidc/callback/")
        assert (
            Account.objects.get(provider="google-oidc").provider_account_id
            == "https://accounts.google.com|pairwise-sub"
        )

    def test_refuses_an_unverified_email(self, instance, google_idp):
        _, response, _ = self.sign_in(google_idp, email_verified=False)
        assert failed_with(response, "OAUTH_PROVIDER_UNVERIFIED_EMAIL")

    def test_hosted_domain_restricts_to_one_workspace(self, instance, google_idp):
        CONFIG["GOOGLE_OIDC_HOSTED_DOMAIN"] = "piatnica.com.pl"
        _, ok, _ = self.sign_in(google_idp, hd="piatnica.com.pl")
        assert "error_code" not in ok.url
        for hd in ({"hd": "other.com"}, {}):
            _, refused, _ = self.sign_in(google_idp, sub=str(uuid.uuid4()), email="x@piatnica.com.pl", **hd)
            assert failed_with(refused, "OIDC_EMAIL_DOMAIN_NOT_ALLOWED")


@pytest.mark.contract
@pytest.mark.django_db
class TestAccountOwnership:
    """An address alone never takes an account over, and a binding never moves."""

    def test_existing_account_is_not_linked_by_default(self, instance, idp, create_user):
        # somebody registered the address with a password of their own before the owner first signed in
        create_user.set_password("attackers-password")
        create_user.is_password_autoset = False
        create_user.save()
        client, response, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert failed_with(response, "OIDC_ACCOUNT_LINK_REQUIRED")
        assert "_auth_user_id" not in client.session
        assert not Account.objects.filter(provider="entra").exists()
        create_user.refresh_from_db()
        assert create_user.check_password("attackers-password")

    def test_linking_takes_the_account_over_from_whoever_set_a_password(self, instance, idp, create_user):
        CONFIG["ENTRA_LINK_EXISTING_ACCOUNTS"] = "1"
        create_user.set_password("attackers-password")
        create_user.is_password_autoset = False
        create_user.is_email_verified = False
        create_user.save()
        client, response, _ = sign_in(idp, token_kwargs={"email": create_user.email})
        assert "error_code" not in response.url
        create_user.refresh_from_db()
        assert client.session["_auth_user_id"] == str(create_user.id)
        assert not create_user.check_password("attackers-password")
        assert create_user.is_password_autoset and create_user.is_email_verified

    def test_a_binding_is_never_moved_to_another_user(self, db, create_user, create_bot_user):
        from django.test import RequestFactory

        from plane.authentication.adapter.error import AuthenticationException
        from plane.authentication.provider.oidc.adapter import OidcProvider
        from plane.authentication.provider.oidc.registry import get_provider_spec

        Account.objects.create(user=create_user, provider="entra", provider_account_id="x", access_token="")
        adapter = OidcProvider(request=RequestFactory().get("/"), spec=get_provider_spec("entra"))
        adapter.user_data = {"user": {"provider_id": "x"}}
        with pytest.raises(AuthenticationException) as raised:
            adapter.create_update_account(create_bot_user)
        assert raised.value.error_code == AUTHENTICATION_ERROR_CODES["OIDC_IDENTITY_MISMATCH"]
        assert Account.objects.get(provider="entra", provider_account_id="x").user_id == create_user.id

    def test_a_failed_binding_leaves_no_half_created_user(self, instance, idp):
        from django.db import IntegrityError

        with patch.object(Account.objects, "create", side_effect=IntegrityError("race")):
            client, response, _ = sign_in(idp)
        assert failed_with(response, "OIDC_PROVIDER_ERROR")
        assert "_auth_user_id" not in client.session
        assert not User.objects.filter(email="ala.kowalska@piatnica.com.pl").exists()

    def test_link_setting_is_registered_for_every_provider(self):
        keys = {v["key"] for v in oidc_config_variables()}
        assert {
            "ENTRA_LINK_EXISTING_ACCOUNTS",
            "GOOGLE_OIDC_LINK_EXISTING_ACCOUNTS",
            "OIDC_LINK_EXISTING_ACCOUNTS",
        } <= keys

    @pytest.mark.parametrize("claim,accepted", [(True, True), ("true", True), (False, False), ("0", False)])
    def test_entra_email_domain_verification_claim(self, instance, idp, claim, accepted):
        _, response, _ = sign_in(idp, token_kwargs={"xms_edov": claim})
        assert ("error_code" not in response.url) is accepted
        if not accepted:
            assert failed_with(response, "OAUTH_PROVIDER_UNVERIFIED_EMAIL")


@pytest.mark.contract
@pytest.mark.django_db
class TestProviderTransport:
    def test_oversized_answers_are_refused(self, instance, idp):
        idp.oversized_keys = True
        _, response, _ = sign_in(idp)
        assert failed_with(response, "OIDC_PROVIDER_ERROR")

    def test_the_providers_own_refusal_is_logged_without_secrets(self, instance, idp, caplog):
        idp.token_status = 400
        idp.token_payload = {"error": "invalid_client", "error_description": "The OAuth client was not found."}
        client = Client()
        start = client.get(reverse("oidc-initiate", args=["entra"]))
        state = parse_qs(urlparse(start.url).query)["state"][0]
        with caplog.at_level("WARNING", logger="plane.authentication"):
            response = client.get(reverse("oidc-callback", args=["entra"]), {"code": "the-code", "state": state})
        assert failed_with(response, "OIDC_PROVIDER_ERROR")
        assert "invalid_client" in caplog.text and "The OAuth client was not found." in caplog.text
        assert "client-secret" not in caplog.text and "the-code" not in caplog.text


@pytest.mark.contract
@pytest.mark.django_db
class TestIssuerScopedBinding:
    def test_the_same_subject_at_another_issuer_is_another_person(self, instance, idp):
        CONFIG.update(
            {
                "IS_OIDC_ENABLED": "1",
                "OIDC_CLIENT_ID": CLIENT_ID,
                "OIDC_CLIENT_SECRET": "s",
                "OIDC_ISSUER_URL": ISSUER,
            }
        )
        sign_in(idp, provider="oidc", token_kwargs={"email_verified": True, "tid": None, "oid": None})
        # the administrator points the provider at another issuer, which hands out the same subjects
        other = "https://other.example.com"
        CONFIG["OIDC_ISSUER_URL"] = other
        fake = FakeIdp(issuer=other)
        with patch("plane.authentication.provider.oidc.client.pinned_fetch", side_effect=fake.fetch):
            client = Client(HTTP_USER_AGENT="Mozilla/5.0")
            start = client.get(reverse("oidc-initiate", args=["oidc"]))
            query = {k: v[0] for k, v in parse_qs(urlparse(start.url).query).items()}
            fake.id_token = make_token(
                query["nonce"], iss=other, email_verified=True, tid=None, oid=None, email="mallory@piatnica.com.pl"
            )
            client.get(reverse("oidc-callback", args=["oidc"]), {"code": "c", "state": query["state"]})
        # not Ala's account, although the subject is the same
        assert "_auth_user_id" in client.session
        assert User.objects.get(id=client.session["_auth_user_id"]).email == "mallory@piatnica.com.pl"
        assert Account.objects.filter(provider="oidc").count() == 2


# ---- groups mirrored from the provider ----------------------------------------------------------------------
EMAIL = "ala.kowalska@piatnica.com.pl"
GRAPH = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/microsoft.graph.group"
GROUP_A = "11111111-0000-0000-0000-00000000000a"
GROUP_B = "11111111-0000-0000-0000-00000000000b"


@pytest.fixture
def groups_on():
    CONFIG["ENTRA_SYNC_GROUPS"] = "1"


def _graph(*groups):
    return lambda url, kwargs: {"value": [{"id": group_id, "displayName": name} for group_id, name in groups]}


def _person(workspace=None):
    user = User.objects.create(email=EMAIL, username="ala")
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _entra_groups(workspace):
    return {
        group.external_id: group for group in UserGroup.objects.filter(workspace=workspace, source=GroupSource.ENTRA)
    }


@pytest.mark.contract
@pytest.mark.django_db
class TestEntraGroups:
    @pytest.fixture(autouse=True)
    def _person_exists_already(self):
        """The person of these tests has an account before signing in with the provider, which has to be allowed."""
        CONFIG["ENTRA_LINK_EXISTING_ACCOUNTS"] = "1"

    def test_groups_are_only_requested_when_switched_on(self, instance, idp):
        client = Client()
        off = parse_qs(urlparse(client.get(reverse("oidc-initiate", args=["entra"])).url).query)
        CONFIG["ENTRA_SYNC_GROUPS"] = "1"
        on = parse_qs(urlparse(Client().get(reverse("oidc-initiate", args=["entra"])).url).query)

        assert off["scope"] == ["openid profile email"]
        assert on["scope"] == ["openid profile email https://graph.microsoft.com/User.Read"]

    def test_nothing_is_read_from_graph_when_switched_off(self, instance, idp, workspace):
        _person(workspace)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))

        sign_in(idp)

        assert idp.api_calls == []
        assert UserGroup.objects.filter(source=GroupSource.ENTRA).count() == 0

    def test_a_sign_in_mirrors_the_groups_in_every_workspace_of_the_person(self, instance, idp, groups_on, workspace):
        other = Workspace.objects.create(name="Other", slug="other", owner=workspace.owner)
        user = _person(workspace)
        WorkspaceMember.objects.create(workspace=other, member=user, role=5)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"), (GROUP_B, "Poland"))

        _, response, _ = sign_in(idp)

        assert "error_code" not in response.url
        for place in (workspace, other):
            groups = _entra_groups(place)
            assert {group.name for group in groups.values()} == {"Sales", "Poland"}
            assert set(
                UserGroupMember.objects.filter(workspace=place, user=user).values_list("group__external_id", flat=True)
            ) == {GROUP_A, GROUP_B}
        # Graph is asked with the person's own token, nowhere else
        method, url, kwargs = idp.api_calls[0]
        assert url == GRAPH and kwargs["headers"]["Authorization"] == "Bearer secret-access"

    def test_the_mirrored_membership_is_marked_as_managed_outside(self, instance, idp, groups_on, workspace):
        user = _person(workspace)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))

        sign_in(idp)

        membership = UserGroupMember.objects.get(user=user)
        assert membership.managed_externally and membership.role == GroupRole.MEMBER
        assert membership.group.is_external

    def test_leaving_a_group_at_the_provider_removes_only_that_membership(self, instance, idp, groups_on, workspace):
        user = _person(workspace)
        local = UserGroup.objects.create(workspace=workspace, name="Local")
        UserGroupMember.objects.create(workspace=workspace, group=local, user=user)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"), (GROUP_B, "Poland"))
        sign_in(idp)

        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))
        sign_in(idp)

        remaining = set(UserGroupMember.objects.filter(user=user).values_list("group__name", flat=True))
        assert remaining == {"Sales", "Local"}
        # The group itself stays: work items may be assigned to it
        assert UserGroup.objects.filter(external_id=GROUP_B).exists()

    def test_a_group_renamed_at_the_provider_is_renamed_here(self, instance, idp, groups_on, workspace):
        _person(workspace)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))
        sign_in(idp)

        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales team"))
        sign_in(idp)

        assert UserGroup.objects.filter(source=GroupSource.ENTRA).get().name == "Sales team"

    def test_a_name_that_is_taken_is_clarified_instead_of_failing_the_sign_in(
        self, instance, idp, groups_on, workspace
    ):
        _person(workspace)
        UserGroup.objects.create(workspace=workspace, name="Sales")
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))

        _, response, _ = sign_in(idp)

        assert "error_code" not in response.url
        assert _entra_groups(workspace)[GROUP_A].name == "Sales (Entra)"

    def test_graph_failing_does_not_stop_the_sign_in_and_keeps_what_was_mirrored(
        self, instance, idp, groups_on, workspace
    ):
        user = _person(workspace)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))
        sign_in(idp)

        def broken(url, kwargs):
            raise oidc_client.OidcProtocolError("down")

        idp.api["https://graph.microsoft.com/"] = broken
        with patch("plane.authentication.provider.oidc.client.get_json_with_bearer", side_effect=broken):
            client, response, _ = sign_in(idp)

        assert "error_code" not in response.url
        assert client.session["_auth_user_id"] == str(user.id)
        assert UserGroupMember.objects.filter(user=user, managed_externally=True).count() == 1

    def test_a_person_in_no_group_any_more_leaves_them_all(self, instance, idp, groups_on, workspace):
        user = _person(workspace)
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))
        sign_in(idp)

        idp.api["https://graph.microsoft.com/"] = _graph()
        sign_in(idp)

        assert UserGroupMember.objects.filter(user=user).count() == 0

    def test_graph_paging_is_followed_but_never_to_another_host(self, instance, idp, groups_on, workspace):
        _person(workspace)
        pages = iter(
            [
                {
                    "value": [{"id": GROUP_A, "displayName": "Sales"}],
                    "@odata.nextLink": "https://graph.microsoft.com/v1.0/next",
                },
                {"value": [{"id": GROUP_B, "displayName": "Poland"}]},
            ]
        )
        idp.api["https://graph.microsoft.com/"] = lambda url, kwargs: next(pages)

        sign_in(idp)

        assert set(_entra_groups(workspace)) == {GROUP_A, GROUP_B}

        evil = {"value": [{"id": "x", "displayName": "X"}], "@odata.nextLink": "https://evil.example.com/steal"}
        idp.api["https://graph.microsoft.com/"] = lambda url, kwargs: evil
        sign_in(idp)

        assert all("evil" not in call[1] for call in idp.api_calls)
        # Not read in full, so what was mirrored stays
        assert set(_entra_groups(workspace)) == {GROUP_A, GROUP_B}

    def test_a_person_who_joins_a_workspace_later_gets_the_groups_of_their_last_sign_in(
        self, instance, idp, groups_on, workspace
    ):
        user = _person()
        idp.api["https://graph.microsoft.com/"] = _graph((GROUP_A, "Sales"))
        sign_in(idp)
        assert UserGroup.objects.filter(source=GroupSource.ENTRA).count() == 0

        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)

        assert set(_entra_groups(workspace)) == {GROUP_A}
        assert UserGroupMember.objects.filter(user=user, managed_externally=True).count() == 1


GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
SERVICE_ACCOUNT = json.dumps(
    {
        "client_email": "reader@project.iam.gserviceaccount.com",
        "private_key": GOOGLE_KEY.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    }
)


@pytest.mark.contract
@pytest.mark.django_db
class TestGoogleGroups:
    @pytest.fixture(autouse=True)
    def _google(self):
        CONFIG.update(
            {
                "IS_GOOGLE_OIDC_ENABLED": "1",
                "GOOGLE_OIDC_CLIENT_ID": CLIENT_ID,
                "GOOGLE_OIDC_CLIENT_SECRET": "s",
                "GOOGLE_OIDC_LINK_EXISTING_ACCOUNTS": "1",
                "GOOGLE_OIDC_SYNC_GROUPS": "1",
                "GOOGLE_OIDC_GROUPS_ADMIN_EMAIL": "admin@piatnica.com.pl",
                "GOOGLE_OIDC_GROUPS_SERVICE_ACCOUNT": SERVICE_ACCOUNT,
            }
        )

    @pytest.fixture
    def google_idp(self):
        fake = FakeIdp(issuer="https://accounts.google.com")
        fake.api["https://oauth2.googleapis.com/token"] = lambda url, kwargs: {"access_token": "workspace-token"}
        with patch("plane.authentication.provider.oidc.client.pinned_fetch", side_effect=fake.fetch):
            yield fake

    def _sign_in(self, idp):
        claims = {"iss": "https://accounts.google.com", "email_verified": True, "tid": None, "oid": None}
        return sign_in(idp, provider="google-oidc", token_kwargs=claims)

    def test_groups_are_read_with_the_service_account_acting_as_the_admin(self, instance, google_idp, workspace):
        user = _person(workspace)
        google_idp.api["https://admin.googleapis.com/"] = lambda url, kwargs: {
            "groups": [{"id": "g1", "name": "Sales", "email": "sales@piatnica.com.pl"}]
        }

        _, response, _ = self._sign_in(google_idp)

        assert "error_code" not in response.url
        group = UserGroup.objects.get(source=GroupSource.GOOGLE)
        assert group.name == "Sales" and group.external_id == "g1"
        assert UserGroupMember.objects.filter(user=user, group=group, managed_externally=True).exists()
        token_call = next(call for call in google_idp.api_calls if call[1].endswith("/token"))
        assert token_call[2]["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        groups_call = next(call for call in google_idp.api_calls if "admin.googleapis.com" in call[1])
        assert groups_call[2]["params"]["userKey"] == EMAIL
        assert groups_call[2]["headers"]["Authorization"] == "Bearer workspace-token"

    def test_nothing_is_read_without_the_service_account(self, instance, google_idp, workspace):
        CONFIG["GOOGLE_OIDC_GROUPS_SERVICE_ACCOUNT"] = ""
        _person(workspace)

        _, response, _ = self._sign_in(google_idp)

        assert "error_code" not in response.url
        assert google_idp.api_calls == []

    def test_a_broken_service_account_key_does_not_stop_the_sign_in(self, instance, google_idp, workspace):
        CONFIG["GOOGLE_OIDC_GROUPS_SERVICE_ACCOUNT"] = "not json"
        _person(workspace)

        _, response, _ = self._sign_in(google_idp)

        assert "error_code" not in response.url
        assert UserGroup.objects.filter(source=GroupSource.GOOGLE).count() == 0
