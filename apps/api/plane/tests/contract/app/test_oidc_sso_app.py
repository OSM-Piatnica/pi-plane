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
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES
from plane.authentication.provider.oidc.registry import enabled_oidc_providers, oidc_config_variables
from plane.db.models import Account, User
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
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

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
            return FakeResponse(_jwks())
        if url == "https://idp.example.com/token":
            self.exchanged.append(kwargs["data"])
            return FakeResponse({"id_token": self.id_token, "access_token": "secret-access", "refresh_token": "r"})
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
        assert Account.objects.get(provider="oidc").provider_account_id == "pairwise-sub"

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
        assert Account.objects.get(provider="google-oidc").provider_account_id == "pairwise-sub"

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
