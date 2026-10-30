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
GRAPH_ADMIN_UNITS_URL = f"{GRAPH_ROOT}v1.0/me/transitiveMemberOf/microsoft.graph.administrativeUnit"
GRAPH_PROFILE_URL = f"{GRAPH_ROOT}v1.0/me"
# User.Read is the least privilege Microsoft Graph asks for to list one's own memberships and read one's own profile
ENTRA_GROUPS_SCOPE = f"{GRAPH_ROOT}User.Read"
# Listing administrative units needs more (as documented for Graph: delegated AdministrativeUnit.Read.All, which an
# administrator of the tenant has to consent to); it is only asked for when administrative units are switched on
ENTRA_ADMIN_UNITS_SCOPE = f"{GRAPH_ROOT}AdministrativeUnit.Read.All"

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


# The kinds of Entra data that can become groups, with the instance setting (``ENTRA_<name>``) that switches each
# one and whether it is on unless the administrator says otherwise. Today's behaviour (every group) is the default.
KIND_SECURITY = "security"
KIND_MICROSOFT_365 = "microsoft_365"
KIND_DISTRIBUTION = "distribution"
KIND_ADMIN_UNITS = "administrative_units"
KIND_DEPARTMENT = "department"
KIND_COMPANY = "company"
ENTRA_KIND_SETTINGS = {
    KIND_SECURITY: ("GROUPS_SECURITY", True),
    KIND_MICROSOFT_365: ("GROUPS_MICROSOFT_365", True),
    KIND_DISTRIBUTION: ("GROUPS_DISTRIBUTION", True),
    KIND_ADMIN_UNITS: ("GROUPS_ADMIN_UNITS", False),
    KIND_DEPARTMENT: ("GROUPS_DEPARTMENT", False),
    KIND_COMPANY: ("GROUPS_COMPANY", False),
}
GROUP_KINDS = (KIND_SECURITY, KIND_MICROSOFT_365, KIND_DISTRIBUTION)

# The longest attribute value that still fits an external id ("department:" + value) and a group name
MAX_ATTRIBUTE_LENGTH = 200


def entra_kinds(config):
    """The kinds of Entra data switched on in the settings (a setting that is not there keeps its default)."""
    kinds = set()
    for kind, (name, default) in ENTRA_KIND_SETTINGS.items():
        value = str(config.get(name) if config.get(name) is not None else "").strip()
        if (value == "1") if value else default:
            kinds.add(kind)
    return kinds


def classify_group(entry):
    """
    Which kind a Graph group object is: Microsoft 365 (``groupTypes`` has Unified; these back Teams and SharePoint
    sites), else security (``securityEnabled``; mail-enabled security groups too), else a distribution list
    (``mailEnabled`` only). An object that says nothing of these is taken as a security group.
    """
    if "Unified" in (entry.get("groupTypes") or []):
        return KIND_MICROSOFT_365
    if entry.get("securityEnabled"):
        return KIND_SECURITY
    if entry.get("mailEnabled"):
        return KIND_DISTRIBUTION
    return KIND_SECURITY


def _read_pages(url, access_token, params):
    """Every entry of a Graph collection; raises OidcProtocolError when it cannot be read completely."""
    entries = []
    for _ in range(MAX_PAGES):
        page = client.get_json_with_bearer(url, access_token, params=params)
        entries.extend(page.get("value") or [])
        url = page.get("@odata.nextLink")
        params = None
        if not url:
            return entries
        # Only ever follow Graph's own paging links: the token must not be sent anywhere else
        if not str(url).startswith(GRAPH_ROOT):
            raise client.OidcProtocolError("unexpected paging link")
    raise client.OidcProtocolError("too many pages")


def _directory_groups(entries, kinds):
    groups = {}
    for entry in entries:
        if entry.get("id") and classify_group(entry) in kinds:
            external_id = str(entry["id"]).lower()
            groups[external_id] = ExternalGroup(external_id, str(entry.get("displayName") or entry["id"]))
    return groups


def _administrative_unit_groups(entries):
    groups = {}
    for entry in entries:
        if entry.get("id"):
            external_id = f"au:{str(entry['id']).lower()}"
            name = str(entry.get("displayName") or entry["id"])[:MAX_ATTRIBUTE_LENGTH]
            groups[external_id] = ExternalGroup(external_id, f"Administrative unit: {name}")
    return groups


def _attribute_group(prefix, label, value):
    """One group for a profile attribute (department, company); a blank or missing value gives none."""
    value = " ".join(str(value or "").split())[:MAX_ATTRIBUTE_LENGTH] if isinstance(value, str) else ""
    if not value:
        return {}
    external_id = f"{prefix}:{value.lower()}"
    return {external_id: ExternalGroup(external_id, f"{label}: {value}")}


def fetch_entra_groups(access_token, kinds=None):
    """
    The groups of the signed-in person that the settings ask for, through Microsoft Graph with their own token.

    ``kinds`` are the kinds of Entra data to read (all three kinds of group when not given, which is what every
    group means). Directory groups (nested ones included) and the profile are each read with one call chain; when
    one of those fails nothing is returned (``None``), so that the memberships mirrored earlier stay. Administrative
    units are the exception: Graph refuses them to a tenant that has not consented to the permission, so a refusal
    only leaves them out.
    """
    if not access_token:
        return None
    kinds = set(GROUP_KINDS) if kinds is None else set(kinds)
    found = {}
    try:
        group_kinds = kinds & set(GROUP_KINDS)
        if group_kinds:
            entries = _read_pages(
                GRAPH_GROUPS_URL,
                access_token,
                {"$select": "id,displayName,securityEnabled,mailEnabled,groupTypes", "$top": str(PAGE_SIZE)},
            )
            found.update(_directory_groups(entries, group_kinds))
        if kinds & {KIND_DEPARTMENT, KIND_COMPANY}:
            profile = client.get_json_with_bearer(
                GRAPH_PROFILE_URL, access_token, params={"$select": "department,companyName"}
            )
            if KIND_DEPARTMENT in kinds:
                found.update(_attribute_group("department", "Department", profile.get("department")))
            if KIND_COMPANY in kinds:
                found.update(_attribute_group("company", "Company", profile.get("companyName")))
    except client.OidcProtocolError as exc:
        logger.warning("Groups of an Entra sign-in not read: %s", exc)
        return None
    if KIND_ADMIN_UNITS in kinds:
        try:
            entries = _read_pages(
                GRAPH_ADMIN_UNITS_URL, access_token, {"$select": "id,displayName", "$top": str(PAGE_SIZE)}
            )
            found.update(_administrative_unit_groups(entries))
        except client.OidcProtocolError as exc:
            logger.warning(
                "Administrative units of an Entra sign-in not read (does the app have the delegated permission "
                "AdministrativeUnit.Read.All, with admin consent?): %s",
                exc,
            )
    return list(found.values())


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
