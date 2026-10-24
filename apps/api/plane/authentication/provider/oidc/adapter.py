# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import secrets
from urllib.parse import urlencode

from django.db import DatabaseError, IntegrityError
from django.utils import timezone

from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.adapter.oauth import OauthAdapter
from plane.db.models import Account, User, WorkspaceMemberInvite
from plane.utils.exception_logger import log_exception

from . import client
from .spec import OidcClaimsError

SESSION_NONCE = "oidc_nonce"
SESSION_VERIFIER = "oidc_verifier"
SESSION_PROVIDER = "oidc_provider"
SESSION_SURFACE = "oidc_surface"


def callback_url(request, key):
    # One callback for every surface (app and spaces), so that a single redirect URI is registered at the provider
    return f"{'https' if request.is_secure() else 'http'}://{request.get_host()}/auth/oidc/{key}/callback/"


def _error(code, payload=None):
    return AuthenticationException(
        error_code=AUTHENTICATION_ERROR_CODES[code], error_message=code, payload=payload or {}
    )


class OidcProvider(OauthAdapter):
    """Signs people in through any provider described by an OidcProviderSpec."""

    def __init__(self, request, spec, code=None, state=None, callback=None):
        self.spec = spec
        self.config = spec.load_config()
        if not spec.is_configured(self.config):
            raise _error("OIDC_NOT_CONFIGURED")
        self.issuer = spec.issuer(self.config)
        redirect_uri = callback_url(request, spec.key)
        super().__init__(
            request,
            spec.key,
            self.config["CLIENT_ID"],
            spec.scopes,
            redirect_uri,
            None,
            None,
            None,
            self.config["CLIENT_SECRET"],
            code,
            callback=callback,
        )
        self.state = state

    def authentication_error_code(self):
        return "OIDC_PROVIDER_ERROR"

    def _discovery(self):
        try:
            return client.get_discovery(self.issuer)
        except client.OidcProtocolError:
            self.logger.warning("Could not read the discovery document of %s", self.provider)
            raise _error("OIDC_PROVIDER_ERROR")

    def get_auth_url(self):
        """Where to send the browser; the nonce and PKCE verifier of this sign-in are kept in the session."""
        discovery = self._discovery()
        verifier, challenge = client.new_pkce_pair()
        nonce = secrets.token_urlsafe(32)
        self.request.session[SESSION_NONCE] = nonce
        self.request.session[SESSION_VERIFIER] = verifier
        self.request.session[SESSION_PROVIDER] = self.provider
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": self.scope,
            "redirect_uri": self.redirect_uri,
            "state": self.state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{discovery['authorization_endpoint']}?{urlencode(params)}"

    def set_token_data(self):
        nonce = self.request.session.pop(SESSION_NONCE, None)
        verifier = self.request.session.pop(SESSION_VERIFIER, None)
        if self.request.session.pop(SESSION_PROVIDER, None) != self.provider or not (nonce and verifier):
            raise _error("OIDC_PROVIDER_ERROR")
        discovery = self._discovery()
        try:
            token_response = client.exchange_code(
                discovery,
                client_id=self.client_id,
                client_secret=self.client_secret,
                code=self.code,
                redirect_uri=self.redirect_uri,
                code_verifier=verifier,
            )
            claims = client.validate_id_token(
                token_response.get("id_token"),
                discovery=discovery,
                issuer=self.issuer,
                client_id=self.client_id,
                nonce=nonce,
            )
        except client.OidcProtocolError:
            self.logger.warning("The sign-in with %s was refused", self.provider)
            raise _error("OIDC_PROVIDER_ERROR")
        # Only who the person is gets kept: the tokens are not needed after this point
        super().set_token_data({"claims": claims})

    def set_user_data(self):
        claims = self.token_data["claims"]
        try:
            self.spec.validate_claims(claims, self.config)
            identity = self.spec.map_claims(claims)
        except OidcClaimsError as exc:
            raise _error(exc.code)
        email = self.sanitize_email(identity.email)
        allowed = [d.strip().lower().lstrip("@") for d in (self.config.get("ALLOWED_EMAIL_DOMAINS") or "").split(",")]
        allowed = [d for d in allowed if d]
        if allowed and email.rsplit("@", 1)[-1] not in allowed:
            raise _error("OIDC_EMAIL_DOMAIN_NOT_ALLOWED", {"email": email})
        super().set_user_data(
            {
                "email": email,
                "user": {
                    "first_name": identity.first_name,
                    "last_name": identity.last_name,
                    "display_name": identity.display_name,
                    "provider_id": identity.subject,
                    "is_password_autoset": True,
                },
            }
        )

    def authenticate(self):
        self.set_token_data()
        self.set_user_data()
        return self.complete_login_or_signup()

    # ---- hooks of Adapter.complete_login_or_signup ---------------------------------------------------------------
    def find_existing_user(self, email):
        """The person's account, found by who they are at the provider and only then by their email address.

        An account that is bound to a different identity of this provider is never taken over through its email.
        """
        subject = self.user_data["user"]["provider_id"]
        account = (
            Account.objects.filter(provider=self.provider, provider_account_id=subject).select_related("user").first()
        )
        if account:
            return account.user
        user = User.objects.filter(email=email).first()
        if user and Account.objects.filter(user=user, provider=self.provider).exists():
            raise _error("OIDC_IDENTITY_MISMATCH", {"email": email})
        return user

    def check_signup(self, email):
        """Signing up through a provider is governed by its own setting, not by the one for email sign-up."""
        if self.config.get("ENABLE_SIGNUP") == "0" and not WorkspaceMemberInvite.objects.filter(email=email).exists():
            self.logger.warning("Sign up is disabled for %s and invite is not present", self.provider)
            raise _error("SIGNUP_DISABLED", {"email": email})

    def check_sync_enabled(self):
        return self.config.get("SYNC") == "1"

    def create_update_account(self, user):
        """Records which identity at the provider the user is. No token of the provider is kept."""
        try:
            Account.objects.update_or_create(
                provider=self.provider,
                provider_account_id=self.user_data["user"]["provider_id"],
                defaults={"user": user, "access_token": "", "last_connected_at": timezone.now()},
            )
        except (DatabaseError, IntegrityError) as e:
            log_exception(e)
