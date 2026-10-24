# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The OpenID Connect protocol: discovery, key set, token exchange and ID token validation."""

import base64
import hashlib
import secrets

import jwt
import requests
from django.core.cache import cache

from plane.utils.url_security import pinned_fetch

# RS256 is what every mainstream provider signs ID tokens with; never accept "none" or a symmetric algorithm
ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"]
CACHE_SECONDS = 3600
TIMEOUT = 10


class OidcProtocolError(Exception):
    """Something is wrong with the provider's answer; the person only sees a generic provider error."""


def _https(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        raise OidcProtocolError("Endpoint is not https")
    return url


def new_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _get_json(url):
    try:
        response = pinned_fetch("GET", _https(url), timeout=TIMEOUT, headers={"Accept": "application/json"})
        try:
            response.raise_for_status()
            return response.json()
        finally:
            response.close()
    except (requests.RequestException, ValueError) as exc:
        raise OidcProtocolError(str(exc)) from exc


def get_discovery(issuer):
    cache_key = f"oidc:discovery:{hashlib.sha256(issuer.encode()).hexdigest()}"
    document = cache.get(cache_key)
    if document is None:
        document = _get_json(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
        # The document must belong to the issuer we asked for (OIDC Discovery §4.3)
        if document.get("issuer") != issuer:
            raise OidcProtocolError("Issuer mismatch in the discovery document")
        for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            _https(document.get(name))
        cache.set(cache_key, document, CACHE_SECONDS)
    return document


def _get_keys(jwks_uri, refresh=False):
    cache_key = f"oidc:jwks:{hashlib.sha256(jwks_uri.encode()).hexdigest()}"
    keys = None if refresh else cache.get(cache_key)
    if keys is None:
        keys = _get_json(jwks_uri)
        cache.set(cache_key, keys, CACHE_SECONDS)
    return keys


def _signing_key(jwks_uri, token):
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise OidcProtocolError("Malformed token") from exc
    # A key that is not cached may just be new: look again once before refusing the token
    for refresh in (False, True):
        try:
            key_set = jwt.PyJWKSet.from_dict(_get_keys(jwks_uri, refresh=refresh))
        except (jwt.PyJWTError, TypeError, ValueError) as exc:
            raise OidcProtocolError("Malformed key set") from exc
        for jwk in key_set.keys:
            if jwk.key_id == kid:
                return jwk.key
    raise OidcProtocolError("Unknown signing key")


def exchange_code(discovery, *, client_id, client_secret, code, redirect_uri, code_verifier):
    try:
        response = pinned_fetch(
            "POST",
            _https(discovery["token_endpoint"]),
            timeout=TIMEOUT,
            headers={"Accept": "application/json"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": code_verifier,
            },
        )
        try:
            response.raise_for_status()
            return response.json()
        finally:
            response.close()
    except (requests.RequestException, ValueError) as exc:
        raise OidcProtocolError(str(exc)) from exc


def validate_id_token(token, *, discovery, issuer, client_id, nonce):
    """The claims of the ID token, if it is signed by the provider and meant for us, for this very sign-in."""
    if not token:
        raise OidcProtocolError("No ID token")
    key = _signing_key(discovery["jwks_uri"], token)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=ALLOWED_ALGORITHMS,
            audience=client_id,
            issuer=issuer,
            leeway=60,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise OidcProtocolError(str(exc)) from exc
    # Binds the token to the browser session that started the sign-in
    if not (nonce and claims.get("nonce") and secrets.compare_digest(str(claims["nonce"]), nonce)):
        raise OidcProtocolError("Nonce mismatch")
    return claims
