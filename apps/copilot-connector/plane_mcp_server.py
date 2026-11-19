# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Serwer MCP (Model Context Protocol) dla Plane - dostep "na zywo" do zadan.

W odroznieniu od konektora Graph (sync_service.py), ktory KOPIUJE zadania do
Microsoft 365, ten serwer niczego nie kopiuje: Copilot (albo inny klient MCP)
wywoluje narzedzia, a serwer w tej samej chwili pyta REST API Plane.

Serwer jest TYLKO DO ODCZYTU - nie tworzy ani nie zmienia zadan.

Uruchamianie:
  python plane_mcp_server.py                      # stdio (VS Code, Claude Desktop, MCP Inspector)
  python plane_mcp_server.py --transport http     # Streamable HTTP pod /mcp (Copilot, Copilot Studio)

Zmienne srodowiskowe (plik .env):
  PLANE_BASE_URL, PLANE_WORKSPACE_SLUG, PLANE_API_TOKEN   - te same co dla synchronizacji
  PLANE_SSL_CERT_PATH   - plik .pem z pelnym lancuchem certyfikatow serwera Plane (zalecane)
  PLANE_SSL_VERIFY      - "false" wylacza weryfikacje certyfikatu (tylko do testow!)
  PLANE_MCP_CACHE_TTL   - ile sekund trzymac pobrane zadania w pamieci (domyslnie 120)

  MCP_AUTH_MODE         - none | apikey | entra   (domyslnie none)
  MCP_API_KEY           - dla apikey: klient wysyla naglowek "Authorization: Bearer <klucz>"
  MCP_ENTRA_AUDIENCE    - dla entra: dozwolone wartosci 'aud' tokena, po przecinku
                          (np. "api://<client-id>,<client-id>")
  MCP_ENTRA_TENANT_ID   - dla entra: tenant (domyslnie AZURE_TENANT_ID)
  MCP_ENTRA_REQUIRED_SCOPES - dla entra: wymagane scope'y, po przecinku (opcjonalnie)
  MCP_PUBLIC_URL        - publiczny adres serwera, np. https://plane-mcp.firma.pl
  MCP_HOST, MCP_PORT    - adres nasluchu dla HTTP (domyslnie 127.0.0.1:8000)
  MCP_ALLOWED_HOSTS     - dodatkowe dozwolone wartosci naglowka Host, po przecinku
  MCP_ALLOWED_ORIGINS   - dodatkowe dozwolone wartosci naglowka Origin (klienci przegladarkowi)
  MCP_ALLOW_ANONYMOUS   - "true" pozwala wystawic HTTP bez uwierzytelniania poza localhost

Uprawnienia:
  - none / apikey: kazdy, kto ma dostep do serwera, widzi wszystko, co widzi token API Plane.
  - entra: serwer weryfikuje token Entra ID uzytkownika i pokazuje mu dane wedlug
    DEFAULT_ACL_TYPE (ta sama zasada co w synchronizacji):
      precise  - projekty, w ktorych jest czlonkiem, i tylko zadania do niego przypisane
                 (wprost albo przez przypisana grupe),
      project  - wszystkie zadania projektow, w ktorych jest czlonkiem (jak w Plane),
      everyone - wszystko, co widzi token API Plane.
"""
import argparse
import hmac
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import anyio.to_thread
import requests
from dotenv import load_dotenv
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from html_text import html_to_text

load_dotenv(Path(__file__).with_name(".env"))

# W trybie stdio standardowe wyjscie nalezy do protokolu - logi ida wylacznie na stderr.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("plane-mcp")


def _env(name, default=""):
    return (os.getenv(name) or default).strip()


def _env_list(name):
    return [v.strip() for v in _env(name).split(",") if v.strip()]


def _require(name):
    value = _env(name)
    if not value:
        sys.exit("Brakuje zmiennej srodowiskowej '" + name + "' (plik .env).")
    return value


PLANE_BASE_URL = _require("PLANE_BASE_URL").rstrip("/")
PLANE_WORKSPACE_SLUG = _require("PLANE_WORKSPACE_SLUG")
PLANE_API_TOKEN = _require("PLANE_API_TOKEN")
# PLANE_API_URL: adres, pod ktorym wolamy API (np. wewnetrzny http://api:8000); linki do zadan
# zawsze z publicznego PLANE_BASE_URL.
API_ROOT = (_env("PLANE_API_URL") or PLANE_BASE_URL).rstrip("/") + "/api/v1/workspaces/" + PLANE_WORKSPACE_SLUG

CACHE_TTL = int(_env("PLANE_MCP_CACHE_TTL", "120"))
STRUCTURE_TTL = 300          # projekty, czlonkowie, stany zmieniaja sie rzadko
MAX_ITEMS_PER_PROJECT = 5000
MAX_DESCRIPTION_CHARS = 12000

AUTH_MODE = _env("MCP_AUTH_MODE", "none").lower()
if AUTH_MODE not in ("none", "apikey", "entra"):
    sys.exit("MCP_AUTH_MODE musi miec wartosc: none, apikey albo entra.")

# W trybie entra: ta sama zasada co ACL synchronizacji (DEFAULT_ACL_TYPE).
VISIBILITY = _env("DEFAULT_ACL_TYPE", "precise").lower()
if VISIBILITY not in ("precise", "project", "everyone"):
    sys.exit("DEFAULT_ACL_TYPE musi miec wartosc: precise, project albo everyone.")


# --------------------------------------------------------------------------- #
# Klient REST API Plane
# --------------------------------------------------------------------------- #

class PlaneError(ToolError):
    """Przewidziany blad: jego tresc trafia do modelu jako czytelny komunikat (ToolError)."""


def _ssl_verify():
    cert = _env("PLANE_SSL_CERT_PATH")
    if cert:
        path = Path(cert)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        return str(path)
    if _env("PLANE_SSL_VERIFY", "true").lower() in ("0", "false", "no"):
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        log.warning("PLANE_SSL_VERIFY=false - certyfikat serwera Plane NIE jest weryfikowany.")
        return False
    return True


_session = requests.Session()
_session.headers["X-Api-Key"] = PLANE_API_TOKEN
_session.verify = _ssl_verify()


def _get(path, params=None):
    """GET do API Plane; ponawia przy limicie zapytan (429) i tlumaczy bledy na czytelne komunikaty."""
    url = API_ROOT + path
    for attempt in range(4):
        try:
            response = _session.get(url, params=params, timeout=30)
        except requests.exceptions.SSLError:
            raise PlaneError(
                "Nie mozna zweryfikowac certyfikatu SSL serwera Plane. Ustaw PLANE_SSL_CERT_PATH "
                "na plik .pem z pelnym lancuchem certyfikatow (albo, tylko do testow, PLANE_SSL_VERIFY=false)."
            )
        except requests.exceptions.RequestException as e:
            raise PlaneError("Brak polaczenia z Plane (" + type(e).__name__ + ").")

        if response.status_code == 429 and attempt < 3:
            try:
                wait = float(response.headers.get("Retry-After", "2"))
            except ValueError:
                wait = 2.0
            time.sleep(min(max(wait, 1.0), 10.0))
            continue
        break

    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            raise PlaneError("Plane zwrocil odpowiedz, ktora nie jest JSON-em (" + path + ").")

    if "html" in response.headers.get("content-type", ""):
        raise PlaneError(
            "Adres " + PLANE_BASE_URL + " odpowiedzial strona HTML (HTTP " + str(response.status_code) + ") "
            "zamiast API Plane. Sprawdz PLANE_BASE_URL oraz czy serwer jest osiagalny z tej sieci (VPN, reverse proxy)."
        )
    hints = {
        401: "token API Plane jest nieprawidlowy albo wygasl",
        403: "token API Plane nie ma dostepu do tego zasobu",
        404: "nie znaleziono zasobu w Plane",
        429: "przekroczono limit zapytan do API Plane - sprobuj za chwile",
    }
    raise PlaneError("Plane: HTTP " + str(response.status_code) + " - " + hints.get(response.status_code, "blad serwera"))


def _get_all(path, params=None, cap=MAX_ITEMS_PER_PROJECT):
    """Pobiera wszystkie strony wyniku (Plane stronicuje kursorem, max 100 na strone)."""
    params = dict(params or {}, per_page=100)
    results = []
    while True:
        page = _get(path, params)
        if isinstance(page, list):
            return page
        results.extend(page.get("results", []))
        if not page.get("next_page_results") or not page.get("next_cursor") or len(results) >= cap:
            return results[:cap]
        params["cursor"] = page["next_cursor"]


_cache = {}
_cache_lock = threading.Lock()


def _cached(key, ttl, loader):
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now + ttl, value)
    return value


def _all_projects():
    return _cached("projects", STRUCTURE_TTL, lambda: _get_all("/projects/"))


GUEST_ROLE = 5


def _member_rows(project_id):
    """Surowa lista czlonkow. 'project-members-lite' podaje tez role, is_active i is_bot; starsze
    wersje Plane go nie maja - wtedy zwykle 'members/' (bez rol: nikt nie jest traktowany jak gosc)."""
    try:
        return _get_all("/projects/" + project_id + "/project-members-lite/")
    except PlaneError as e:
        if "HTTP 404" not in str(e):
            raise
        return _get_all("/projects/" + project_id + "/members/")


def _members(project_id):
    """Aktywni czlonkowie projektu (bez kont botow) jako lista {id, name, email, role}."""
    def load():
        members = []
        for raw in _member_rows(project_id):
            user = raw.get("member") if isinstance(raw.get("member"), dict) else raw
            if raw.get("is_active") is False or raw.get("is_bot") or user.get("is_bot"):
                continue
            members.append({
                "id": user.get("id"),
                "name": user.get("display_name") or " ".join(
                    p for p in (user.get("first_name"), user.get("last_name")) if p) or user.get("email") or "",
                "email": (user.get("email") or raw.get("email") or "").strip().lower(),
                "role": raw.get("role"),
            })
        return members
    return _cached("members:" + project_id, STRUCTURE_TTL, load)


def _states(project_id):
    return _cached("states:" + project_id, STRUCTURE_TTL, lambda: _get_all("/projects/" + project_id + "/states/"))


def _items(project_id):
    def load():
        try:
            return _get_all("/projects/" + project_id + "/work-items/", {"expand": "assignees,state"})
        except PlaneError as e:
            if "HTTP 403" in str(e):
                return e  # brak dostepu tez zapamietujemy - inaczej kazde wyszukiwanie pytaloby Plane od nowa
            raise

    value = _cached("items:" + project_id, CACHE_TTL, load)
    if isinstance(value, PlaneError):
        raise value
    return value


def _group_members(project_id):
    """{id grupy: zbior id osob} dla grup, do ktorych mozna przypisac zadania projektu."""
    def load():
        try:
            rows = _get("/projects/" + project_id + "/groups/", {"assignable": 1, "members": 1})
        except PlaneError:
            return {}
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        return {str(g["id"]): set(g["member_ids"]) for g in rows if "member_ids" in g}
    return _cached("groups:" + project_id, STRUCTURE_TTL, load)


def _is_assigned(item, user_id, project_id):
    """Czy osoba jest przypisana do zadania - wprost albo przez przypisana grupe."""
    for assignee in item.get("assignees") or []:
        if str(assignee.get("id") if isinstance(assignee, dict) else assignee) == user_id:
            return True
    group_ids = item.get("group_assignee_ids") or []
    if group_ids:
        groups = _group_members(project_id)
        return any(user_id in groups.get(str(group_id), ()) for group_id in group_ids)
    return False


def _visible_items(project):
    """Zadania projektu, ktore pytajacy moze zobaczyc (tryb entra, wedlug DEFAULT_ACL_TYPE).
    Zawsze tez tak jak w Plane: gosc bez "guest_view_all_features" widzi tylko zadania,
    ktore sam utworzyl."""
    items = _items(project["id"])
    if AUTH_MODE != "entra" or VISIBILITY == "everyone":
        return items
    email = _current_email()
    me = next((m for m in _members(project["id"]) if email and m["email"] == email), None)
    if me is None:
        return []
    my_id = str(me["id"])
    if me.get("role") == GUEST_ROLE and not project.get("guest_view_all_features"):
        items = [item for item in items if str(item.get("created_by")) == my_id]
    if VISIBILITY == "precise":
        lead = project.get("project_lead")
        is_lead = str(lead.get("id") if isinstance(lead, dict) else lead) == my_id
        # zadania bez przypisanych osob widzi lider projektu, ktory projektem zarzadza
        items = [item for item in items
                 if _is_assigned(item, my_id, project["id"]) or (is_lead and _is_unassigned(item, project["id"]))]
    return items


def _is_unassigned(item, project_id):
    """Nie jest przypisany nikt z aktywnych czlonkow projektu - ani wprost, ani przez grupe."""
    active = {str(m["id"]) for m in _members(project_id)}
    assigned = {str(a.get("id") if isinstance(a, dict) else a) for a in item.get("assignees") or []}
    if item.get("group_assignee_ids"):
        groups = _group_members(project_id)
        for group_id in item["group_assignee_ids"]:
            assigned |= {str(u) for u in groups.get(str(group_id), ())}
    return not (assigned & active)


# --------------------------------------------------------------------------- #
# Kto pyta i co mu wolno zobaczyc
# --------------------------------------------------------------------------- #

def _current_email():
    """E-mail zalogowanego uzytkownika (tylko w trybie entra); w pozostalych trybach None."""
    token = get_access_token()
    if token and token.claims:
        return (token.claims.get("email") or "").strip().lower() or None
    return None


def _visible_projects():
    projects = _all_projects()
    if AUTH_MODE != "entra" or VISIBILITY == "everyone":
        return projects

    email = _current_email()
    if not email:
        return []
    visible = []
    for project in projects:
        try:
            if any(m["email"] == email for m in _members(project["id"])):
                visible.append(project)
        except PlaneError:
            continue  # token API nie widzi czlonkow projektu -> nie pokazujemy go
    return visible


def _resolve_project(ref):
    """Znajduje projekt po identyfikatorze (np. 'OSM'), nazwie albo UUID - wsrod projektow widocznych dla pytajacego."""
    projects = _visible_projects()
    needle = (ref or "").strip().casefold()
    for field in ("id", "identifier", "name"):
        for project in projects:
            if str(project.get(field) or "").casefold() == needle:
                return project
    partial = [p for p in projects if needle and needle in str(p.get("name") or "").casefold()]
    if len(partial) == 1:
        return partial[0]
    available = ", ".join(sorted(_label(p) for p in projects)) or "(brak dostepnych projektow)"
    raise PlaneError("Nie znaleziono projektu '" + str(ref) + "'. Dostepne projekty: " + available)


def _label(project):
    return str(project.get("identifier") or "?") + " (" + str(project.get("name") or "") + ")"


# --------------------------------------------------------------------------- #
# Zamiana surowych danych Plane na zwiezla postac dla modelu
# --------------------------------------------------------------------------- #

def _state_name(project_id, state):
    if isinstance(state, dict):
        return state.get("name")
    if isinstance(state, str):
        try:
            return next((s.get("name") for s in _states(project_id) if s.get("id") == state), state)
        except PlaneError:
            return state
    return None


def _assignee_names(project_id, assignees):
    names = []
    for assignee in assignees or []:
        if isinstance(assignee, dict):
            names.append(assignee.get("display_name") or assignee.get("email") or "")
        elif isinstance(assignee, str):
            try:
                names.append(next((m["name"] for m in _members(project_id) if m["id"] == assignee), assignee))
            except PlaneError:
                names.append(assignee)
    return [n for n in names if n]


def _key(project, item):
    return str(project.get("identifier") or "?") + "-" + str(item.get("sequence_id") or "?")


def _description(item):
    stripped = item.get("description_stripped")
    return stripped if isinstance(stripped, str) and stripped.strip() else html_to_text(item.get("description_html"))


def _summary(project, item):
    project_id = project["id"]
    return {
        "key": _key(project, item),
        "title": item.get("name") or "",
        "project": project.get("name") or "",
        "state": _state_name(project_id, item.get("state")),
        "priority": item.get("priority") or "none",
        "assignees": _assignee_names(project_id, item.get("assignees")),
        "updated_at": item.get("updated_at"),
        "target_date": item.get("target_date"),
        "url": PLANE_BASE_URL + "/" + PLANE_WORKSPACE_SLUG + "/projects/" + project_id + "/issues/" + item["id"],
    }


_KEY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)-(\d+)\s*$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _find_item(key):
    """Zwraca (projekt, zadanie) dla klucza 'OSM-123' albo UUID zadania."""
    key = (key or "").strip()
    match = _KEY_RE.match(key)
    if match:
        project = _resolve_project(match.group(1))
        for item in _visible_items(project):
            if str(item.get("sequence_id")) == match.group(2):
                return project, item
        raise PlaneError("Nie znaleziono zadania " + key.upper() + " w projekcie " + _label(project) + ".")
    if _UUID_RE.match(key):
        for project in _visible_projects():
            try:
                for item in _visible_items(project):
                    if item.get("id") == key.lower():
                        return project, item
            except PlaneError:
                continue
        raise PlaneError("Nie znaleziono zadania o identyfikatorze " + key + ".")
    raise PlaneError("Podaj klucz zadania w postaci PROJEKT-NUMER (np. OSM-123) albo UUID zadania.")


def _clamp(value, low, high):
    return max(low, min(int(value), high))


# --------------------------------------------------------------------------- #
# Narzedzia MCP
# --------------------------------------------------------------------------- #

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

INSTRUCTIONS = (
    "Read-only access to the company's Plane project-management instance (projects and work items / tasks; "
    "content is mostly in Polish). Work items are addressed by a key such as 'OSM-123' "
    "(project identifier + number). Typical flow: list_projects -> search_work_items or list_work_items -> "
    "get_work_item for the full description. Always cite the work item key and url in answers."
)


def build_server(token_verifier=None, auth=None):
    mcp = MCPServer(
        name="plane",
        title="Plane",
        description="Zadania i projekty z Plane (tylko odczyt).",
        instructions=INSTRUCTIONS,
        token_verifier=token_verifier,
        auth=auth,
    )

    @mcp.tool(title="List Plane projects", annotations=READ_ONLY)
    def list_projects() -> list[dict]:
        """List the Plane projects the current user can access (identifier, name, description).
        Use the 'identifier' (e.g. 'OSM') or the name as the 'project' argument of other tools."""
        return [{
            "identifier": p.get("identifier"),
            "name": p.get("name"),
            "description": (p.get("description") or "")[:500],
            "id": p.get("id"),
        } for p in _visible_projects()]

    @mcp.tool(title="Search Plane work items", annotations=READ_ONLY)
    def search_work_items(query: str, project: str | None = None, limit: int = 20) -> dict:
        """Full-text search over work item titles and descriptions. Every word of 'query' must occur
        (case-insensitive); a key such as 'OSM-123' matches that item directly.
        Optionally restrict to one project (identifier or name). Returns the best matches with a text snippet."""
        terms = [t for t in query.casefold().split() if t]
        if not terms:
            raise PlaneError("Podaj tekst do wyszukania.")
        projects = [_resolve_project(project)] if project else _visible_projects()
        hits, skipped = [], []
        for proj in projects:
            try:
                items = _visible_items(proj)
            except PlaneError:
                skipped.append(proj.get("name"))
                continue
            for item in items:
                title = (item.get("name") or "").casefold()
                key = _key(proj, item).casefold()
                body = _description(item)
                body_cf = body.casefold()
                if not all(t in title or t in body_cf or t == key for t in terms):
                    continue
                score = sum(3 if (t in title or t == key) else 1 for t in terms)
                entry = _summary(proj, item)
                position = min((body_cf.find(t) for t in terms if t in body_cf), default=-1)
                if position >= 0:
                    start = max(0, position - 80)
                    entry["snippet"] = ("..." if start else "") + body[start:start + 240].replace("\n", " ")
                hits.append((score, item.get("updated_at") or "", entry))
        hits.sort(key=lambda h: (h[0], h[1]), reverse=True)
        limit = _clamp(limit, 1, 50)
        result = {"total_matches": len(hits), "results": [h[2] for h in hits[:limit]]}
        if skipped:
            result["projects_skipped_no_access"] = skipped
        return result

    @mcp.tool(title="List Plane work items", annotations=READ_ONLY)
    def list_work_items(
        project: str,
        state: str | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        updated_after: str | None = None,
        limit: int = 50,
    ) -> dict:
        """List work items of one project, newest changes first, with optional filters:
        state (name fragment, e.g. 'In Progress'), assignee (name or e-mail fragment; 'none' = unassigned),
        priority (urgent/high/medium/low/none), updated_after (ISO date, e.g. '2026-11-01').
        'total_matching' is the full count even when 'limit' truncates the list."""
        proj = _resolve_project(project)
        rows = []
        for item in _visible_items(proj):
            row = _summary(proj, item)
            if state and state.casefold() not in (row["state"] or "").casefold():
                continue
            if priority and priority.casefold() != row["priority"].casefold():
                continue
            if assignee:
                wanted = assignee.casefold()
                people = " ".join(
                    row["assignees"] + [a.get("email") or "" for a in item.get("assignees") or [] if isinstance(a, dict)]
                ).casefold()
                if (wanted == "none") != (not row["assignees"]) or (wanted != "none" and wanted not in people):
                    continue
            if updated_after and (row["updated_at"] or "") < updated_after:
                continue
            rows.append(row)
        rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
        return {"project": _label(proj), "total_matching": len(rows), "items": rows[:_clamp(limit, 1, 200)]}

    @mcp.tool(title="Get Plane work item", annotations=READ_ONLY)
    def get_work_item(key: str) -> dict:
        """Get one work item with its full plain-text description, dates and labels.
        'key' is e.g. 'OSM-123' (or the work item UUID)."""
        proj, cached = _find_item(key)
        try:
            item = _get("/projects/" + proj["id"] + "/work-items/" + cached["id"] + "/",
                        {"expand": "assignees,state,labels"})
        except PlaneError:
            item = cached
        description = _description(item)
        result = _summary(proj, item)
        result.update({
            "description": description[:MAX_DESCRIPTION_CHARS],
            "description_truncated": len(description) > MAX_DESCRIPTION_CHARS,
            "labels": [label.get("name") for label in item.get("labels") or [] if isinstance(label, dict)],
            "start_date": item.get("start_date"),
            "created_at": item.get("created_at"),
            "created_by": next((m["name"] for m in _members(proj["id"]) if str(m["id"]) == str(item.get("created_by"))), ""),
            "completed_at": item.get("completed_at"),
        })
        return result

    @mcp.tool(title="List Plane work item comments", annotations=READ_ONLY)
    def list_work_item_comments(key: str, limit: int = 20) -> dict:
        """List the newest comments of a work item ('key' e.g. 'OSM-123') as plain text."""
        proj, item = _find_item(key)
        raw = _get_all("/projects/" + proj["id"] + "/work-items/" + item["id"] + "/comments/", cap=500)
        names = {m["id"]: m["name"] for m in _members(proj["id"])}
        comments = []
        for c in raw:
            actor = c.get("actor_detail") if isinstance(c.get("actor_detail"), dict) else {}
            author_id = c.get("actor") or c.get("created_by")
            comments.append({
                "author": actor.get("display_name") or names.get(author_id) or "",
                "created_at": c.get("created_at"),
                "text": (c.get("comment_stripped") or html_to_text(c.get("comment_html")))[:4000],
            })
        comments.sort(key=lambda c: c["created_at"] or "", reverse=True)
        return {"key": _key(proj, item), "total": len(comments), "comments": comments[:_clamp(limit, 1, 100)]}

    @mcp.tool(title="Get Plane project details", annotations=READ_ONLY)
    def get_project_details(project: str) -> dict:
        """Project overview: workflow states with the number of work items in each, priorities breakdown and members.
        Use it for questions like 'how many tasks are in progress in project X' or 'who works on X'."""
        proj = _resolve_project(project)
        by_state, by_priority = {}, {}
        items = _visible_items(proj)
        for item in items:
            state = _state_name(proj["id"], item.get("state")) or "?"
            by_state[state] = by_state.get(state, 0) + 1
            priority = item.get("priority") or "none"
            by_priority[priority] = by_priority.get(priority, 0) + 1
        try:
            states = [{"name": s.get("name"), "group": s.get("group"), "work_items": by_state.get(s.get("name"), 0)}
                      for s in _states(proj["id"])]
        except PlaneError:
            states = [{"name": n, "work_items": c} for n, c in by_state.items()]
        try:
            members = [{"name": m["name"], "email": m["email"]} for m in _members(proj["id"])]
        except PlaneError:
            members = []
        return {
            "identifier": proj.get("identifier"),
            "name": proj.get("name"),
            "description": proj.get("description") or "",
            "total_work_items": len(items),
            "states": states,
            "work_items_by_priority": by_priority,
            "members": members,
        }

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request):
        return JSONResponse({"status": "ok", "auth": AUTH_MODE})

    return mcp


# --------------------------------------------------------------------------- #
# Uwierzytelnianie klientow serwera MCP (tylko transport HTTP)
# --------------------------------------------------------------------------- #

class StaticKeyVerifier:
    """Tryb apikey: jeden wspolny klucz w naglowku 'Authorization: Bearer <klucz>'."""

    def __init__(self, key):
        self._key = key.encode()

    async def verify_token(self, token):
        if hmac.compare_digest(token.encode(), self._key):
            return AccessToken(token=token, client_id="api-key", scopes=[])
        return None


class EntraVerifier:
    """Tryb entra: sprawdza podpis, wystawce, tenant, odbiorce i waznosc tokena dostepu Entra ID."""

    def __init__(self, tenant_id, audiences):
        import jwt  # PyJWT[crypto]

        self._jwt = jwt
        self._tenant = tenant_id
        self._audiences = audiences
        self._issuers = {
            "https://login.microsoftonline.com/" + tenant_id + "/v2.0",
            "https://sts.windows.net/" + tenant_id + "/",
        }
        self._jwks = jwt.PyJWKClient(
            "https://login.microsoftonline.com/" + tenant_id + "/discovery/v2.0/keys", cache_keys=True)

    async def verify_token(self, token):
        return await anyio.to_thread.run_sync(self._verify, token)

    def _verify(self, token):
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token).key
            claims = self._jwt.decode(
                token, signing_key, algorithms=["RS256"], audience=self._audiences,
                options={"require": ["exp", "iss", "aud"]},
            )
        except Exception as e:
            log.info("Odrzucono token Entra: %s", type(e).__name__)
            return None
        if claims.get("iss") not in self._issuers or claims.get("tid") != self._tenant:
            log.info("Odrzucono token Entra: obcy wystawca lub tenant")
            return None
        email = (claims.get("preferred_username") or claims.get("upn") or claims.get("email")
                 or claims.get("unique_name") or "")
        return AccessToken(
            token=token,
            client_id=claims.get("azp") or claims.get("appid") or "",
            scopes=(claims.get("scp") or "").split(),
            expires_at=claims.get("exp"),
            subject=claims.get("oid") or claims.get("sub"),
            claims={"email": email.strip().lower(), "name": claims.get("name"), "iss": claims["iss"]},
        )


def _auth_for_http(public_url):
    if AUTH_MODE == "apikey":
        key = _env("MCP_API_KEY")
        if len(key) < 24:
            sys.exit("MCP_AUTH_MODE=apikey wymaga MCP_API_KEY o dlugosci co najmniej 24 znakow.")
        return StaticKeyVerifier(key), AuthSettings(
            issuer_url=public_url, resource_server_url=None, validate_token_resource=False)

    if AUTH_MODE == "entra":
        tenant = _env("MCP_ENTRA_TENANT_ID") or _require("AZURE_TENANT_ID")
        audiences = _env_list("MCP_ENTRA_AUDIENCE")
        if not audiences:
            sys.exit("MCP_AUTH_MODE=entra wymaga MCP_ENTRA_AUDIENCE (np. api://<client-id>).")
        return EntraVerifier(tenant, audiences), AuthSettings(
            issuer_url="https://login.microsoftonline.com/" + tenant + "/v2.0",
            resource_server_url=public_url,
            validate_token_resource=False,  # odbiorce ('aud') sprawdza EntraVerifier
            required_scopes=_env_list("MCP_ENTRA_REQUIRED_SCOPES") or None,
        )

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Serwer MCP dla Plane (tylko odczyt)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default=_env("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(_env("MCP_PORT", "8000")))
    args = parser.parse_args()

    if args.transport == "stdio":
        if AUTH_MODE != "none":
            log.warning("MCP_AUTH_MODE=%s dotyczy tylko transportu HTTP - w stdio jest ignorowany.", AUTH_MODE)
        build_server().run("stdio")
        return

    is_local = args.host in ("127.0.0.1", "localhost", "::1")
    public_url = _env("MCP_PUBLIC_URL") or "http://" + ("localhost" if is_local else args.host) + ":" + str(args.port)
    public_url = public_url.rstrip("/")

    if AUTH_MODE == "none" and (not is_local or _env("MCP_PUBLIC_URL")) and _env("MCP_ALLOW_ANONYMOUS").lower() != "true":
        sys.exit(
            "Odmowa startu: serwer bylby dostepny poza localhost bez uwierzytelniania, a pokazuje wszystko, "
            "co widzi token API Plane. Ustaw MCP_AUTH_MODE=entra lub apikey (albo swiadomie MCP_ALLOW_ANONYMOUS=true)."
        )

    verifier, auth = _auth_for_http(public_url)

    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"] + _env_list("MCP_ALLOWED_HOSTS")
    public_host = urlparse(public_url).netloc
    if public_host:
        allowed_hosts += [public_host, public_host + ":*"]

    log.info("Plane MCP: %s/mcp (nasluch %s:%s, uwierzytelnianie: %s)", public_url, args.host, args.port, AUTH_MODE)
    build_server(verifier, auth).run(
        "streamable-http",
        host=args.host,
        port=args.port,
        stateless_http=True,   # bez sesji po stronie serwera - dziala za load balancerem / reverse proxy
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=allowed_hosts,
            # Dotyczy tylko klientow przegladarkowych (np. MCP Inspector); Copilot nie wysyla naglowka Origin.
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
            + _env_list("MCP_ALLOWED_ORIGINS"),
        ),
    )


if __name__ == "__main__":
    main()
