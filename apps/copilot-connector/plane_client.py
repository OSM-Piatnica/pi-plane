# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Klient do pobierania danych z REST API Plane (/api/v1, naglowek X-Api-Key).
Token: bot token z God Mode (docs/bot-tokens.md) - widzi wszystkie projekty, tylko odczyt.

CERTYFIKAT SSL (tylko gdy PLANE_API_URL to https):
certyfikat serwera jest weryfikowany. Jesli serwer wysyla niekompletny lancuch
certyfikatow, ustaw PLANE_SSL_CERT_PATH na plik .pem z certyfikatem posrednim
i glownym. PLANE_SSL_VERIFY=false wylacza weryfikacje (tylko do testow!).
W stosie Pi-Plane konektor wola API wewnetrznie (http://api:8000), bez certyfikatu.
"""
import os
import time
from pathlib import Path

import requests
import urllib3
from config import settings

HEADERS = {"X-Api-Key": settings.PLANE_API_TOKEN}
TIMEOUT = 60
# Plane pozwala na 60 zapytan na minute na token; pelna synchronizacja wielu projektow
# przekracza ten limit, wiec po HTTP 429 czekamy i probujemy ponownie.
MAX_RATE_LIMIT_RETRIES = 5
GUEST_ROLE = 5


def _ssl_verify():
    cert = settings.PLANE_SSL_CERT_PATH
    if cert:
        path = Path(cert)
        if not path.is_absolute():
            path = Path(__file__).parent / path
        return str(path)
    if (os.getenv("PLANE_SSL_VERIFY") or "").strip().lower() in ("0", "false", "no"):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("UWAGA: PLANE_SSL_VERIFY=false - certyfikat serwera Plane NIE jest weryfikowany.")
        return False
    return True


_VERIFY = _ssl_verify()


def _base_url():
    return f"{settings.PLANE_API_URL}/api/v1/workspaces/{settings.PLANE_WORKSPACE_SLUG}"


def _get(url, params=None):
    """GET do API Plane z ponawianiem po przekroczeniu limitu zapytan (HTTP 429)."""
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        response = requests.get(url, headers=HEADERS, params=params, verify=_VERIFY, timeout=TIMEOUT)
        if response.status_code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
            break
        wait = _retry_after(response)
        print(f"  Limit zapytan Plane - czekam {wait} s...")
        time.sleep(wait)
    response.raise_for_status()
    return response.json()


def _retry_after(response):
    try:
        return max(1, min(int(float(response.headers.get("Retry-After", "")) + 1), 65))
    except ValueError:
        return 30


def _all_pages(url, params=None):
    params = dict(params or {}, per_page=100)
    results = []
    while True:
        data = _get(url, params)
        if isinstance(data, list):
            return data
        results.extend(data.get("results", []))
        if not data.get("next_page_results") or not data.get("next_cursor"):
            return results
        params["cursor"] = data["next_cursor"]


def list_projects():
    """Zwraca liste wszystkich projektow w workspace (wszystkie strony)."""
    return _all_pages(f"{_base_url()}/projects/")


def list_project_people(project_id):
    """
    Wszyscy, ktorzy sa lub byli w projekcie (z e-mailem, rola i flagami is_active / is_bot).
    Nieaktywnych potrzebujemy tylko po to, zeby podpisac imieniem autora starszych zadan.

    Endpoint 'project-members-lite' podaje role (5 = gosc); starsze wersje Plane
    go nie maja - wtedy zwykle 'members/' (sami aktywni, role = None).
    """
    try:
        rows = _all_pages(f"{_base_url()}/projects/{project_id}/project-members-lite/")
    except requests.exceptions.HTTPError as e:
        if e.response is None or e.response.status_code != 404:
            raise
        rows = _all_pages(f"{_base_url()}/projects/{project_id}/members/")

    people = []
    for row in rows:
        user = row.get("member") if isinstance(row.get("member"), dict) else row
        people.append({
            "id": user.get("id"),
            "email": (user.get("email") or row.get("email") or "").strip().lower(),
            "display_name": user.get("display_name") or " ".join(
                p for p in (user.get("first_name"), user.get("last_name")) if p) or "",
            "role": row.get("role"),
            "is_active": row.get("is_active") is not False,
            "is_bot": bool(row.get("is_bot") or user.get("is_bot")),
        })
    return people


def list_project_members(project_id):
    """
    Aktywni czlonkowie projektu, bez kont botow (np. bota z tokena god-mode,
    ktory jest czlonkiem wszystkich projektow). Na nich budowane jest ACL.
    """
    return [p for p in list_project_people(project_id) if p["is_active"] and not p["is_bot"]]


def list_group_members(project_id):
    """
    {id grupy: zbior id osob} dla grup, do ktorych mozna przypisac zadania projektu
    (grupa obejmuje tez osoby z grup ponizej niej). Pusty slownik, gdy serwer Plane
    nie podaje sklad grup (wersja bez parametru 'members').
    """
    data = _get(f"{_base_url()}/projects/{project_id}/groups/", {"assignable": 1, "members": 1})
    rows = data.get("results", data) if isinstance(data, dict) else data
    return {str(g["id"]): set(g["member_ids"]) for g in rows if "member_ids" in g}


def list_work_items(project_id, cursor=None):
    """
    Zwraca jedna strone zadan (work items) dla danego projektu.
    Plane zwraca dane stronicowane (max 100 na strone).
    """
    url = f"{_base_url()}/projects/{project_id}/work-items/"
    # Bez "state" w expand Plane zwraca w polu 'state' samo UUID stanu zamiast jego nazwy.
    params = {"per_page": 100, "expand": "assignees,state"}
    if cursor:
        params["cursor"] = cursor

    return _get(url, params)


def list_all_work_items(project_id):
    """Pobiera WSZYSTKIE zadania z projektu, automatycznie przechodzac przez kolejne strony."""
    items = []
    cursor = None

    while True:
        page = list_work_items(project_id, cursor=cursor)
        items.extend(page.get("results", []))

        if not page.get("next_page_results"):
            break
        cursor = page.get("next_cursor")

    return items
