# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The groups a person belongs to at their identity provider, read at sign-in.

A fetch returns the list of groups, or ``None`` when the groups could not be read (not configured, or the
provider refused): ``None`` leaves the memberships mirrored earlier as they are, whereas an empty list means the
person is in no group any more and removes them.
"""

import json
import logging
import time
from dataclasses import dataclass

import jwt

from . import client

logger = logging.getLogger("plane.authentication")

GRAPH_ROOT = "https://graph.microsoft.com/"
GRAPH_GROUPS_URL = f"{GRAPH_ROOT}v1.0/me/transitiveMemberOf/microsoft.graph.group"
# User.Read is the least privilege Microsoft Graph asks for to list one's own memberships
ENTRA_GROUPS_SCOPE = f"{GRAPH_ROOT}User.Read"

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_GROUPS_URL = "https://admin.googleapis.com/admin/directory/v1/groups"
GOOGLE_GROUPS_SCOPE = "https://www.googleapis.com/auth/admin.directory.group.readonly"

# A person is in a handful of groups; this stops a provider that never ends its pages
MAX_PAGES = 20
PAGE_SIZE = 200


@dataclass(frozen=True)
class ExternalGroup:
    id: str
    name: str


def fetch_entra_groups(access_token):
    """Every group of the signed-in person, nested ones included, through Microsoft Graph with their own token."""
    if not access_token:
        return None
    groups = {}
    url = GRAPH_GROUPS_URL
    params = {"$select": "id,displayName", "$top": str(PAGE_SIZE)}
    try:
        for _ in range(MAX_PAGES):
            page = client.get_json_with_bearer(url, access_token, params=params)
            for entry in page.get("value") or []:
                if entry.get("id"):
                    groups[str(entry["id"]).lower()] = ExternalGroup(
                        str(entry["id"]).lower(), str(entry.get("displayName") or entry["id"])
                    )
            url = page.get("@odata.nextLink")
            params = None
            # Only ever follow Graph's own paging links: the token must not be sent anywhere else
            if not url:
                return list(groups.values())
            if not str(url).startswith(GRAPH_ROOT):
                logger.warning("Groups of an Entra sign-in not read: unexpected paging link")
                return None
    except client.OidcProtocolError as exc:
        logger.warning("Groups of an Entra sign-in not read: %s", exc)
        return None
    logger.warning("Groups of an Entra sign-in not read: too many pages")
    return None


def _google_access_token(service_account, admin_email):
    """An access token of the service account acting as the Workspace admin (domain-wide delegation)."""
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": service_account["client_email"],
            "sub": admin_email,
            "scope": GOOGLE_GROUPS_SCOPE,
            "aud": GOOGLE_TOKEN_URL,
            "iat": now,
            "exp": now + 300,
        },
        service_account["private_key"],
        algorithm="RS256",
    )
    answer = client.post_form(
        GOOGLE_TOKEN_URL,
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
    )
    return answer.get("access_token")


def fetch_google_groups(email, service_account_json, admin_email):
    """The Google Workspace groups the person is a direct member of, read with the Admin SDK Directory API."""
    if not (email and service_account_json and admin_email):
        return None
    try:
        service_account = json.loads(service_account_json)
        if not (service_account.get("client_email") and service_account.get("private_key")):
            raise ValueError("incomplete key")
    except (TypeError, ValueError):
        logger.warning("Groups of a Google sign-in not read: the service account key is not valid")
        return None
    groups = {}
    try:
        token = _google_access_token(service_account, admin_email)
        if not token:
            return None
        page_token = None
        for _ in range(MAX_PAGES):
            params = {"userKey": email, "maxResults": str(PAGE_SIZE)}
            if page_token:
                params["pageToken"] = page_token
            page = client.get_json_with_bearer(GOOGLE_GROUPS_URL, token, params=params)
            for entry in page.get("groups") or []:
                if entry.get("id"):
                    groups[str(entry["id"])] = ExternalGroup(
                        str(entry["id"]), str(entry.get("name") or entry.get("email") or entry["id"])
                    )
            page_token = page.get("nextPageToken")
            if not page_token:
                return list(groups.values())
    except (client.OidcProtocolError, jwt.PyJWTError, ValueError) as exc:
        logger.warning("Groups of a Google sign-in not read: %s", type(exc).__name__)
        return None
    logger.warning("Groups of a Google sign-in not read: too many pages")
    return None


# A person is in a handful of groups; a claim with more is not a list of groups
MAX_CLAIM_GROUPS = 500


def groups_from_claim(claims, claim_name):
    """
    The groups named by a claim of the ID token: a list of names, or one string of names separated by commas.

    A claim the token does not carry says nothing about the person's groups, so it gives ``None`` (nothing
    changes); a claim that is there and empty means they are in no group.
    """
    claim_name = (claim_name or "").strip()
    if not claim_name or claim_name not in claims:
        return None
    value = claims[claim_name]
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, (list, tuple)) or len(value) > MAX_CLAIM_GROUPS:
        logger.warning("Groups of a sign-in not read: the claim is not a list of groups")
        return None
    groups = {}
    for entry in value:
        if not isinstance(entry, str):
            continue
        # Keycloak writes the path of a group ("/sales/poland"); the name is shown without the leading slash
        name = entry.strip().lstrip("/").strip()
        if name:
            groups[name.lower()] = ExternalGroup(name.lower(), name[:255])
    return list(groups.values())
