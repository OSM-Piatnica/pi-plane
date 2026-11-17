# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
An app-only Microsoft Graph client for SharePoint.

Pi-Plane signs in as itself (OAuth 2.0 client credentials: one POST to the tenant's token endpoint, so no MSAL) and
is meant to hold the application permission ``Sites.Selected``, which lets it reach only the sites an administrator
granted to it. See ``docs/sharepoint.md``.

How the module is laid out, for whoever adds to it (upload sessions, download URLs, thumbnails and versions come
with the document store):

- ``SharePointClient._send`` is the only place that touches the network: time-outs, a cap on the size of an answer,
  and the bounded retry on 429 and 503 that honours ``Retry-After``.
- ``SharePointClient.get_token`` asks for a token through it and keeps the token in the cache until shortly before
  it expires.
- ``SharePointClient.request`` is the one way to call Graph: it adds the token, refreshes it once when Graph answers
  401, and turns an error answer into one of the exceptions of ``errors.py``. A new Graph call is a small method
  that builds a path from validated IDs and calls ``request`` (or ``request_pages`` for a collection).
- Only ``https://graph.microsoft.com/v1.0`` is ever sent the token. Bytes that travel to a pre-authenticated URL
  (an upload session, a download URL) must not go through ``request``: those URLs are on other hosts and take no
  bearer token.

Nothing here writes the client secret or a token to a log or into an error.
"""

import hashlib
import json as json_module
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote, urlsplit

import httpx
from django.core.cache import cache as default_cache

from .errors import (
    SharePointAuthError,
    SharePointError,
    SharePointInputError,
    SharePointNotFoundError,
    SharePointPermissionError,
    SharePointResponseError,
    SharePointThrottledError,
    SharePointTransportError,
)

logger = logging.getLogger("plane.external")

LOGIN_ROOT = "https://login.microsoftonline.com"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Seconds: connecting, and waiting for each part of an answer
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
# Site, library and item metadata is a few kilobytes; a page of a collection some hundreds. Nothing is megabytes.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
# A request is tried this many times in all when Graph answers 429 or 503 (or, for a GET, does not answer)
MAX_ATTEMPTS = 4
# The longest a request waits between its tries, all waits together. A longer Retry-After is not slept through:
# the caller gets a SharePointThrottledError that says how long Graph asked for.
DEFAULT_MAX_WAIT = 20.0
# The wait before the next try when Graph names none: 1 s, 2 s, 4 s
BACKOFF = 1.0
THROTTLED_STATUSES = (429, 503)
# A token is dropped this long before Microsoft would stop accepting it
TOKEN_EXPIRY_MARGIN = 300
# A collection is read in pages; this stops an answer that never ends them
MAX_PAGES = 20

_GUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
_GUID_RE = re.compile(_GUID)
# A tenant is named by its ID or by one of its domains (contoso.onmicrosoft.com)
_DOMAIN_RE = re.compile(r"(?=.{4,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")
# SharePoint Online in the worldwide cloud: <tenant>.sharepoint.com (and <tenant>-my for OneDrive). The national
# clouds have their own Graph and sign-in hosts, which this client does not talk to.
_SHAREPOINT_HOST_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.sharepoint\.com")
# What Graph calls a site: "<hostname>,<site collection id>,<web id>"
_SITE_ID_RE = re.compile(rf"[a-z0-9.-]{{1,253}},{_GUID},{_GUID}", re.IGNORECASE)
# A drive ID is URL-safe base64 with a "b!" in front for a document library
_DRIVE_ID_RE = re.compile(r"[A-Za-z0-9!_-]{1,200}")
# Parts of a pasted address that belong to a page or a library, not to the site: the site ends before them
_NOT_SITE_SEGMENTS = {"shared documents", "sitepages", "siteassets", "lists", "forms"}
MAX_SITE_URL_LENGTH = 2000
MAX_SITE_PATH_SEGMENTS = 10

# Why Microsoft refused to issue a token, by the AADSTS number in its answer
_TOKEN_ERROR_CODES = {
    7000215: "invalid_credentials",  # invalid client secret provided
    7000222: "secret_expired",  # the provided client secret keys are expired
    700016: "application_not_found",  # application was not found in the directory
    90002: "tenant_not_found",  # tenant not found
    900023: "tenant_not_found",  # the tenant identifier is not a valid DNS name or domain
}
_TOKEN_ERROR_MESSAGES = {
    "invalid_credentials": "Microsoft did not accept the client secret. Check that the secret value (not its ID) was "
    "pasted and that it belongs to this application.",
    "secret_expired": "The client secret has expired. Create a new one in the app registration and save it here.",
    "application_not_found": "Microsoft does not know this client ID in this tenant. Check the application (client) "
    "ID and that the app is registered in the tenant named here.",
    "tenant_not_found": "Microsoft does not know this tenant. Check the directory (tenant) ID.",
    "authentication_failed": "Microsoft refused to sign the application in.",
}


def validate_tenant_id(value) -> str:
    """The tenant as it goes into the address of the token endpoint: its ID (a GUID) or one of its domains."""
    text = str(value or "").strip().lower()
    if _GUID_RE.fullmatch(text) or _DOMAIN_RE.fullmatch(text):
        return text
    raise SharePointInputError(
        "The tenant ID must be the directory (tenant) ID, for example 72f988bf-86f1-41af-91ab-2d7cd011db47, "
        "or a domain of the tenant.",
        code="invalid_tenant_id",
    )


def validate_client_id(value) -> str:
    """The application (client) ID of the app registration: always a GUID."""
    text = str(value or "").strip().lower()
    if _GUID_RE.fullmatch(text):
        return text
    raise SharePointInputError(
        "The client ID must be the application (client) ID of the app registration, "
        "for example 6731de76-14a6-49ae-97bc-6eba6914391e.",
        code="invalid_client_id",
    )


@dataclass(frozen=True)
class SiteAddress:
    """Where a site lives: the SharePoint host and the path of the site on it ("" for the root site)."""

    hostname: str
    path: str

    @property
    def graph_path(self) -> str:
        """The Graph address of the site by its path, each part encoded."""
        if not self.path:
            return f"/sites/{self.hostname}"
        encoded = "/".join(quote(segment, safe="") for segment in self.path.split("/"))
        return f"/sites/{self.hostname}:/{encoded}"


def _invalid_site_url(reason: str) -> SharePointInputError:
    return SharePointInputError(
        f"{reason} Paste the address of the site's home page, for example https://contoso.sharepoint.com/sites/Projects.",
        code="invalid_site_url",
    )


def parse_site_url(url) -> SiteAddress:
    """
    Take a pasted SharePoint address apart into host and site path, or raise SharePointInputError.

    Only ``https://<tenant>.sharepoint.com/...`` is accepted. The host is never requested: it becomes part of a path
    on graph.microsoft.com, so the server cannot be pointed anywhere else. What follows the site in a pasted address
    (a page, ``Shared Documents``, ``_layouts/...``) is dropped. A sub-site keeps its whole path.
    """
    text = str(url or "").strip()
    if not text:
        raise _invalid_site_url("The site URL is empty.")
    if len(text) > MAX_SITE_URL_LENGTH or "\\" in text or any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise _invalid_site_url("The site URL is not a valid address.")
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise _invalid_site_url("The site URL is not a valid address.") from None
    if parts.scheme.lower() != "https":
        raise _invalid_site_url("The site URL must start with https://.")
    if parts.username is not None or parts.password is not None or port not in (None, 443):
        raise _invalid_site_url("The site URL must not carry a user name or a port.")
    hostname = (parts.hostname or "").lower()
    if not _SHAREPOINT_HOST_RE.fullmatch(hostname):
        raise _invalid_site_url("The site URL must be on a SharePoint Online host (<tenant>.sharepoint.com).")

    segments = []
    # Split first, decode after: an encoded slash must not turn into a new part of the path
    for raw_segment in parts.path.split("/"):
        segment = unquote(raw_segment).strip()
        if not segment:
            continue
        if segment.startswith("_") or segment.lower() in _NOT_SITE_SEGMENTS or segment.lower().endswith(".aspx"):
            break
        if (
            segment in (".", "..")
            or any(char in segment for char in '/\\:"<>|*?')
            or any(ord(char) < 32 or ord(char) == 127 for char in segment)
        ):
            raise _invalid_site_url("The site URL has a part that cannot be in a site address.")
        segments.append(segment)
    if len(segments) > MAX_SITE_PATH_SEGMENTS:
        raise _invalid_site_url("The site URL is nested too deep.")
    return SiteAddress(hostname=hostname, path="/".join(segments))


def _site_id_path(site_id) -> str:
    text = str(site_id or "").strip()
    if not _SITE_ID_RE.fullmatch(text):
        raise SharePointInputError("This is not the ID of a SharePoint site.", code="invalid_site_id")
    return quote(text, safe=",")


def _drive_id_path(drive_id) -> str:
    text = str(drive_id or "").strip()
    if not _DRIVE_ID_RE.fullmatch(text):
        raise SharePointInputError("This is not the ID of a document library.", code="invalid_drive_id")
    return quote(text, safe="!")


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    web_url: str

    @classmethod
    def from_graph(cls, data: dict) -> "Site":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("displayName") or data.get("name") or ""),
            web_url=str(data.get("webUrl") or ""),
        )


@dataclass(frozen=True)
class Drive:
    """A document library of a site."""

    id: str
    name: str
    web_url: str
    drive_type: str

    @classmethod
    def from_graph(cls, data: dict) -> "Drive":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            web_url=str(data.get("webUrl") or ""),
            drive_type=str(data.get("driveType") or ""),
        )


@dataclass(frozen=True)
class DriveItem:
    """A file or folder of a library; for now only what the root folder needs."""

    id: str
    name: str
    web_url: str
    etag: str
    is_folder: bool

    @classmethod
    def from_graph(cls, data: dict) -> "DriveItem":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            web_url=str(data.get("webUrl") or ""),
            etag=str(data.get("eTag") or ""),
            is_folder="folder" in data,
        )


def _retry_after(headers) -> float | None:
    """What Retry-After asks for in seconds (it is a number of seconds or an HTTP date); None when it says nothing."""
    raw = (headers.get("Retry-After") or "").strip()
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


class SharePointClient:
    """
    Talks to Microsoft Graph as the application itself. One instance per piece of work; ``close()`` it or use it in
    a ``with`` block. ``transport``, ``cache`` and ``sleep`` are there for the tests, which run without a network.
    """

    def __init__(
        self,
        tenant_id,
        client_id,
        client_secret,
        *,
        transport: httpx.BaseTransport | None = None,
        cache=None,
        sleep=time.sleep,
        max_wait: float = DEFAULT_MAX_WAIT,
    ):
        self._tenant_id = validate_tenant_id(tenant_id)
        self._client_id = validate_client_id(client_id)
        self._client_secret = str(client_secret or "").strip()
        if not self._client_secret:
            raise SharePointInputError("The client secret is empty.", code="invalid_client_secret")
        self._cache = default_cache if cache is None else cache
        self._sleep = sleep
        self._max_wait = max_wait
        # Texts that must never leave this object in a message: the secret, and each token as it is issued
        self._confidential = {self._client_secret}
        # Never follow a redirect (the token would travel with it) and never pick up proxy settings or credentials
        # from the environment of the process
        self._http = httpx.Client(transport=transport, timeout=TIMEOUT, follow_redirects=False, trust_env=False)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __repr__(self):
        return f"SharePointClient(tenant_id={self._tenant_id!r}, client_id={self._client_id!r})"

    def close(self):
        self._http.close()

    # ------------------------------------------------------------------ transport

    def _scrub(self, text) -> str:
        """`text`, shortened, with the secret and any token taken out: for a message a person or a log may see."""
        cleaned = str(text or "")
        for confidential in self._confidential:
            cleaned = cleaned.replace(confidential, "***")
        return cleaned[:300]

    def _read(self, response: httpx.Response):
        """The JSON body of the answer, read with a cap on its size; None when there is none or it is not JSON."""
        chunks, total = [], 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise SharePointTransportError("Microsoft sent an answer that is too large.")
            chunks.append(chunk)
        if not total:
            return None
        try:
            return json_module.loads(b"".join(chunks))
        except ValueError:
            if response.status_code < 400:
                raise SharePointTransportError("Microsoft sent an answer that is not JSON.") from None
            return None

    def _send(self, method: str, url: str, *, what: str, **kwargs):
        """
        One HTTP exchange with Microsoft, and the only code here that touches the network. Returns the status and the
        parsed body. Tries again, a bounded number of times and for a bounded time, when the answer is 429 or 503
        (waiting as long as ``Retry-After`` says) and, for a GET, when no answer arrives.
        """
        waited = 0.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            last_attempt = attempt == MAX_ATTEMPTS
            fallback_wait = BACKOFF * 2 ** (attempt - 1)
            try:
                with self._http.stream(method, url, **kwargs) as response:
                    status = response.status_code
                    wait = _retry_after(response.headers)
                    payload = self._read(response)
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                # The exception is not chained or quoted: it carries the request, whose body may hold the secret
                reason = type(exc).__name__
                logger.warning("SharePoint: %s got no answer (%s), attempt %s", what, reason, attempt)
                if method == "GET" and not last_attempt and waited + fallback_wait <= self._max_wait:
                    self._sleep(fallback_wait)
                    waited += fallback_wait
                    continue
                timed_out = isinstance(exc, httpx.TimeoutException)
                raise SharePointTransportError(
                    "Microsoft did not answer in time." if timed_out else "Microsoft could not be reached.",
                    detail=reason,
                ) from None

            if status not in THROTTLED_STATUSES:
                logger.debug("SharePoint: %s answered %s", what, status)
                return status, payload

            pause = fallback_wait if wait is None else wait
            logger.warning("SharePoint: %s answered %s (retry after %s s), attempt %s", what, status, wait, attempt)
            if last_attempt or waited + pause > self._max_wait:
                raise SharePointThrottledError(
                    "Microsoft is limiting requests right now. Try again later.", retry_after=wait, status=status
                )
            self._sleep(pause)
            waited += pause
        raise SharePointThrottledError("Microsoft is limiting requests right now. Try again later.")  # not reached

    # ------------------------------------------------------------------ token

    @property
    def _token_cache_key(self) -> str:
        # The secret is part of the key (hashed), so a token issued for an old secret is not used after a change
        identity = f"{self._tenant_id}\0{self._client_id}\0{self._client_secret}"
        return f"sharepoint:token:{hashlib.sha256(identity.encode()).hexdigest()}"

    def forget_token(self):
        self._cache.delete(self._token_cache_key)

    def get_token(self, *, force_refresh: bool = False) -> str:
        """
        An access token for Graph, from the cache or, when there is none (or ``force_refresh``), from the tenant's
        token endpoint. It is kept until five minutes before it expires.
        """
        if not force_refresh:
            token = self._cache.get(self._token_cache_key)
            if token:
                self._confidential.add(token)
                return token

        status, payload = self._send(
            "POST",
            f"{LOGIN_ROOT}/{quote(self._tenant_id, safe='')}/oauth2/v2.0/token",
            what="token request",
            headers={"Accept": "application/json"},
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": GRAPH_SCOPE,
            },
        )
        payload = payload if isinstance(payload, dict) else {}
        if status >= 400:
            raise self._token_error(status, payload)
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise SharePointTransportError("Microsoft answered the sign-in without a token.")
        self._confidential.add(token)
        try:
            lifetime = int(payload.get("expires_in") or 0)
        except (TypeError, ValueError):
            lifetime = 0
        if lifetime > TOKEN_EXPIRY_MARGIN:
            self._cache.set(self._token_cache_key, token, lifetime - TOKEN_EXPIRY_MARGIN)
        return token

    def _token_error(self, status: int, payload: dict) -> SharePointError:
        error = str(payload.get("error") or "")
        detail = self._scrub(f"{error}: {payload.get('error_description') or ''}".strip(": "))
        if status >= 500:
            return SharePointResponseError(
                "Microsoft's sign-in service answered with an error. Try again later.", detail=detail, status=status
            )
        code = None
        for number in payload.get("error_codes") or []:
            code = _TOKEN_ERROR_CODES.get(number) if isinstance(number, int) else None
            if code:
                break
        if code is None:
            code = "invalid_credentials" if error == "invalid_client" else "authentication_failed"
        return SharePointAuthError(_TOKEN_ERROR_MESSAGES[code], code=code, detail=detail, status=status)

    # ------------------------------------------------------------------ Graph

    @staticmethod
    def _graph_url(path_or_url: str) -> str:
        """A Graph address from a path ("/sites/...") or from a link Graph itself returned (a next page)."""
        if path_or_url.startswith("/") and not path_or_url.startswith("//"):
            return f"{GRAPH_ROOT}{path_or_url}"
        # The token must not be sent anywhere but Graph, whatever an answer says
        if path_or_url.startswith(f"{GRAPH_ROOT}/"):
            return path_or_url
        raise SharePointTransportError("Microsoft sent a link that does not lead to Microsoft Graph.")

    def request(self, method: str, path_or_url: str, *, params: dict | None = None, json=None) -> dict:
        """
        Call Graph and return the JSON answer. Every Graph call of Pi-Plane goes through here. Raises one of the
        errors of ``errors.py``; never returns an error answer.
        """
        url = self._graph_url(path_or_url)
        what = f"{method} {urlsplit(url).path}"
        status, payload = 0, None
        # A token Graph does not accept (revoked, or cached past a change on Microsoft's side) is replaced once
        for force_refresh in (False, True):
            token = self.get_token(force_refresh=force_refresh)
            status, payload = self._send(
                method,
                url,
                what=what,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params=params,
                json=json,
            )
            if status != 401:
                break
        if status >= 400:
            if status == 401:
                self.forget_token()
            raise self._graph_error(status, payload)
        return payload if isinstance(payload, dict) else {}

    def request_pages(self, path: str, *, params: dict | None = None) -> list[dict]:
        """Every entry of a Graph collection, following its own next-page links (and only those)."""
        entries: list[dict] = []
        target: str | None = path
        for _ in range(MAX_PAGES):
            page = self.request("GET", target, params=params)
            entries.extend(entry for entry in (page.get("value") or []) if isinstance(entry, dict))
            target = page.get("@odata.nextLink")
            # The next link already carries the query
            params = None
            if not target:
                return entries
            if not isinstance(target, str):
                break
        raise SharePointTransportError("Microsoft sent a list that does not end.")

    def _graph_error(self, status: int, payload) -> SharePointError:
        error = payload.get("error") if isinstance(payload, dict) else None
        error = error if isinstance(error, dict) else {}
        detail = self._scrub(f"{error.get('code') or ''}: {error.get('message') or ''}".strip(": "))
        if status == 401:
            return SharePointAuthError(
                "Microsoft Graph did not accept the application's token.", detail=detail, status=status
            )
        if status == 403:
            return SharePointPermissionError(
                "Microsoft Graph refused access. The application is not allowed to use this resource.",
                detail=detail,
                status=status,
            )
        if status == 404:
            return SharePointNotFoundError("Microsoft Graph did not find this resource.", detail=detail, status=status)
        return SharePointResponseError(
            f"Microsoft Graph answered with an error (HTTP {status}).", detail=detail, status=status
        )

    # ------------------------------------------------------------------ sites and libraries

    def get_site(self, site_url) -> Site:
        """The site a pasted SharePoint address belongs to (host and server-relative path → site ID)."""
        address = parse_site_url(site_url)
        data = self.request("GET", address.graph_path, params={"$select": "id,displayName,name,webUrl"})
        site = Site.from_graph(data)
        if not site.id:
            raise SharePointTransportError("Microsoft answered without the ID of the site.")
        return site

    def list_drives(self, site_id) -> list[Drive]:
        """The document libraries of a site."""
        entries = self.request_pages(
            f"/sites/{_site_id_path(site_id)}/drives", params={"$select": "id,name,webUrl,driveType"}
        )
        return [Drive.from_graph(entry) for entry in entries if entry.get("id")]

    def get_drive_root(self, drive_id) -> DriveItem:
        """The root folder of a document library."""
        data = self.request(
            "GET", f"/drives/{_drive_id_path(drive_id)}/root", params={"$select": "id,name,webUrl,eTag,folder"}
        )
        item = DriveItem.from_graph(data)
        if not item.id:
            raise SharePointTransportError("Microsoft answered without the ID of the folder.")
        return item
