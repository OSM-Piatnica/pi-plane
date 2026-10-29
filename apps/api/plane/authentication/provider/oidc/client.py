# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The OpenID Connect protocol: discovery, key set, token exchange and ID token validation."""

import base64
import hashlib
import json
import secrets

import jwt
import requests
from django.core.cache import cache

from plane.utils.url_security import pinned_fetch

# RS256 is what every mainstream provider signs ID tokens with; never accept "none" or a symmetric algorithm
ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"]
CACHE_SECONDS = 3600
TIMEOUT = 10
# Discovery documents, key sets and token answers are a few kilobytes; anything bigger is not from a provider
MAX_RESPONSE_BYTES = 1024 * 1024


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


def _read_json(response):
    """The JSON body of the response, read with a cap on its size."""
    chunks, total = [], 0
    for chunk in response.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise OidcProtocolError("Response too large")
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks))
    except ValueError as exc:
        raise OidcProtocolError("Response is not JSON") from exc


def _refusal(response):
    """What the provider says about its refusal: only the standard OAuth fields, truncated (never the request)."""
    try:
        body = _read_json(response)
        return f"{body.get('error', '')}: {str(body.get('error_description', ''))[:200]}"
    except (OidcProtocolError, AttributeError):
        return ""


def _request_json(method, url, headers=None, **kwargs):
    try:
        response = pinned_fetch(
            method,
            _https(url),
            timeout=TIMEOUT,
            headers={"Accept": "application/json", **(headers or {})},
            stream=True,
            **kwargs,
        )
        try:
            if response.status_code >= 400:
                detail = _refusal(response)
                raise OidcProtocolError(
                    f"Provider returned HTTP {response.status_code}" + (f" ({detail})" if detail else "")
                )
            return _read_json(response)
        finally:
            response.close()
    except (requests.RequestException, ValueError) as exc:
        raise OidcProtocolError(f"{type(exc).__name__}: {exc}") from exc


def _get_json(url):
    return _request_json("GET", url)


def get_json_with_bearer(url, token, params=None):
    """A GET of a provider's API with an access token; the answer is read with the same caps as the sign-in."""
    return _request_json("GET", url, headers={"Authorization": f"Bearer {token}"}, params=params)


def post_form(url, data):
    return _request_json("POST", url, data=data)


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
    return _request_json(
        "POST",
        discovery["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        },
    )


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
