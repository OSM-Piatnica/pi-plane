# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Synchronizacja zadan z Plane do Microsoft 365 (Copilot). W stosie Pi-Plane uruchamia ja
cyklicznie scheduler.py; recznie: python sync_service.py [--full] [--allow-mass-delete].

Kto widzi zadanie w Copilocie, ustala DEFAULT_ACL_TYPE (patrz ProjectAccess):
  precise  - tylko osoby przypisane do zadania (wprost albo przez przypisana grupe);
             zadanie bez przypisanych osob widzi lider projektu,
  project  - wszyscy czlonkowie projektu, jak w samym Plane,
  everyone - wszyscy w firmie.
Zadania usuniete w Plane sa usuwane takze z Copilota (stan w sync_state.json).

Jesli token API nie ma dostepu do jakiegos projektu (np. blad 403), taki
projekt jest POMIJANY, a na koncu wypisywana jest zbiorcza lista pominietych
projektow - reszta synchronizacji dziala normalnie dalej.
"""
import argparse
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import requests
from config import settings
from graph_auth import get_access_token
from html_text import html_to_text
from graph_users import resolve_user_object_id
from plane_client import GUEST_ROLE, list_all_work_items, list_group_members, list_project_people, list_projects

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers():
    return {
        "Authorization": "Bearer " + get_access_token(),
        "Content-Type": "application/json",
    }


def _extract_status_name(state_field):
    """Pole 'state' bywa stringiem albo slownikiem - obsluguje oba przypadki."""
    if isinstance(state_field, str):
        return state_field
    if isinstance(state_field, dict):
        return state_field.get("name", "Nieznany")
    return "Nieznany"


def _extract_description(item):
    """
    API Plane (v1) zwraca opis tylko w 'description_html' - pola 'description_stripped'
    i 'description' sa puste. Najpierw bierzemy gotowy tekst, a gdy go brak - czyscimy HTML.
    """
    return (
        item.get("description_stripped")
        or (item.get("description") if isinstance(item.get("description"), str) else None)
        or html_to_text(item.get("description_html"))
    )


_object_ids = {}


def _object_id(email):
    """Object ID konta w Entra ID dla e-maila z Plane (z pamiecia - te same osoby sa w wielu projektach)."""
    if email not in _object_ids:
        _object_ids[email] = resolve_user_object_id(email)
    return _object_ids[email]


def _user_acl_entry(object_id):
    return {
        "type": "user",
        "value": object_id,
        "accessType": "grant",
        "identitySource": "azureActiveDirectory",
    }


ACL_MODES = {
    # kazdy w firmie widzi kazde zadanie
    "everyone",
    # jak w Plane: czlonkowie projektu widza wszystkie jego zadania (goscie - tylko swoje)
    "project",
    # tylko osoby przypisane do zadania (wprost albo przez przypisana grupe), ktore sa w projekcie
    "precise",
}


def _assignee_ids(item):
    """Id osob przypisanych wprost (pole 'assignees' bywa lista slownikow albo samych id)."""
    ids = set()
    for assignee in item.get("assignees") or []:
        ids.add(str(assignee.get("id") if isinstance(assignee, dict) else assignee))
    return ids


def _project_lead_id(project):
    """Id lidera projektu ('Project lead' w ustawieniach projektu w Plane) albo None."""
    lead = project.get("project_lead")
    if isinstance(lead, dict):
        lead = lead.get("id")
    return str(lead) if lead else None


class ProjectAccess:
    """
    Kto z projektu Plane moze zobaczyc dane zadanie w Copilocie (wedlug DEFAULT_ACL_TYPE).

    Zawsze obowiazuje tez to, co widac w samym Plane: osoba musi byc aktywnym czlonkiem
    projektu (nie bot), a gosc bez "guest_view_all_features" widzi tylko zadania, ktore
    sam utworzyl. Konto w Entra ID dobierane jest po e-mailu (UPN).
    """

    def __init__(self, project):
        self.project = project
        self.mode = settings.DEFAULT_ACL_TYPE
        self.guests_see_all = bool(project.get("guest_view_all_features"))
        self.lead_id = _project_lead_id(project)
        self._groups = None
        self._warned_groups = set()
        people = list_project_people(project["id"])
        self.names = {str(p["id"]): p["display_name"] or p["email"] for p in people}
        self.active_ids = {str(p["id"]) for p in people if p["is_active"] and not p["is_bot"]}
        self.roles = {}
        self.entries = {}
        not_found = []
        if self.mode == "everyone":
            return
        for person in people:
            if not person["is_active"] or person["is_bot"] or not person["email"]:
                continue
            object_id = _object_id(person["email"])
            if not object_id:
                not_found.append(person["email"])
                continue
            self.roles[str(person["id"])] = person["role"]
            self.entries[str(person["id"])] = _user_acl_entry(object_id)
        if not_found:
            print("  Bez konta w Entra ID (nie zobacza zadan w Copilocie): " + ", ".join(sorted(not_found)))

    def _sees_in_plane(self, user_id, item):
        if self.roles.get(user_id) != GUEST_ROLE or self.guests_see_all:
            return True
        return str(item.get("created_by")) == user_id

    def _group_members(self, group_id):
        if self._groups is None:
            try:
                self._groups = list_group_members(self.project["id"])
            except requests.exceptions.HTTPError:
                self._groups = {}
        members = self._groups.get(str(group_id))
        if members is None and group_id not in self._warned_groups:
            self._warned_groups.add(group_id)
            print("  UWAGA: nie znam skladu grupy " + str(group_id)
                  + " - jej czlonkowie nie zobacza zadan przypisanych tylko do grupy.")
        return members or set()

    def assigned_user_ids(self, item):
        ids = _assignee_ids(item)
        for group_id in item.get("group_assignee_ids") or []:
            ids |= {str(user_id) for user_id in self._group_members(group_id)}
        return ids

    def acl_for(self, item):
        if self.mode == "everyone":
            return [{
                "type": "everyone",
                "value": settings.AZURE_TENANT_ID,
                "accessType": "grant",
                "identitySource": "azureActiveDirectory",
            }]
        if self.mode == "precise":
            candidates = self.assigned_user_ids(item) & self.active_ids
            if not candidates and self.lead_id:
                # nikt (z aktywnych czlonkow projektu) nie jest przypisany - zadanie widzi
                # lider projektu, ktory projektem zarzadza
                candidates = {self.lead_id}
        else:
            candidates = set(self.entries)
        return [self.entries[user_id] for user_id in sorted(candidates)
                if user_id in self.entries and self._sees_in_plane(user_id, item)]

    def creator_name(self, item):
        return self.names.get(str(item.get("created_by")), "")


def _map_work_item_to_external_item(project, item, acl, created_by_name=""):
    item_id = item["id"]
    project_id = project["id"]
    workspace_slug = settings.PLANE_WORKSPACE_SLUG

    item_url = settings.PLANE_BASE_URL + "/" + workspace_slug + "/projects/" + project_id + "/issues/" + item_id

    assignees = item.get("assignees", []) or []
    assigned_names = ", ".join(a.get("display_name") or a.get("email", "") for a in assignees)
    if not assigned_names:
        assigned_names = "Nieprzypisane"

    description = _extract_description(item)
    title = item.get("name", "Bez tytulu")
    status = _extract_status_name(item.get("state"))
    priority = item.get("priority") or "none"
    project_name = project.get("name", "")
    project_url = settings.PLANE_BASE_URL + "/" + workspace_slug + "/projects/" + project_id + "/issues/"

    item_key = ""
    if project.get("identifier") and item.get("sequence_id") is not None:
        item_key = str(project["identifier"]) + "-" + str(item["sequence_id"])

    # Copilot indeksuje semantycznie tylko tytul i 'content'. Dlatego content zawiera
    # nie sam opis, ale tez tytul i metadane - inaczej zadania bez opisu maja pusty
    # content, a pytania typu "jaki status ma zadanie X" nie maja sie o co oprzec.
    content_lines = [
        "Zadanie" + (" " + item_key if item_key else "") + ": " + title,
        "Projekt: " + project_name,
        "Status: " + status,
        "Priorytet: " + priority,
        "Przypisane do: " + assigned_names,
    ]
    if created_by_name:
        content_lines.append("Utworzone przez: " + created_by_name)
    if item.get("start_date"):
        content_lines.append("Data rozpoczecia: " + str(item["start_date"]))
    if item.get("target_date"):
        content_lines.append("Termin: " + str(item["target_date"]))
    if description:
        content_lines.append("")
        content_lines.append("Opis:")
        content_lines.append(description)

    properties = {
        "title": title,
        "url": item_url,
        "description": description,
        "status": status,
        "assignedTo": assigned_names,
        "projectName": project_name,
        "lastModified": item.get("updated_at") or item.get("created_at"),
        "priority": priority,
        "iconUrl": settings.PLANE_ICON_URL,
        "projectUrl": project_url,
        "itemKey": item_key,
        "createdBy": created_by_name,
    }
    if item.get("created_at"):
        properties["created"] = item["created_at"]

    return {
        "id": project_id + "_" + item_id,
        "acl": acl,
        "properties": properties,
        "content": {
            "value": "\n".join(content_lines),
            "type": "text",
        },
    }


def _push_item(external_item):
    connection_id = settings.GRAPH_CONNECTION_ID
    item_id = external_item["id"]
    url = GRAPH_BASE + "/external/connections/" + connection_id + "/items/" + item_id

    title = external_item["properties"]["title"]
    try:
        response = requests.put(url, headers=_headers(), json=external_item, timeout=60)
    except requests.exceptions.RequestException as e:
        print("  BLAD przy '" + title + "': " + type(e).__name__)
        return False

    if response.status_code == 200:
        print("  OK: " + title)
        return True

    # Przy awarii Graph odpowiedzia bywa cala strona HTML - wypisujemy tylko poczatek.
    print("  BLAD przy '" + title + "': " + str(response.status_code) + " " + response.text[:300].replace("\n", " "))
    return False


def _remove_item(item_id, reason):
    """Usuwa element z Graph. True, gdy go tam juz nie ma (usuniety albo nigdy nie istnial)."""
    url = GRAPH_BASE + "/external/connections/" + settings.GRAPH_CONNECTION_ID + "/items/" + item_id
    try:
        response = requests.delete(url, headers=_headers(), timeout=60)
    except requests.exceptions.RequestException as e:
        print("  BLAD usuwania " + item_id + ": " + type(e).__name__)
        return False
    if response.status_code in (200, 204):
        print("  USUNIETO z Copilota (" + reason + "): " + item_id)
        return True
    if response.status_code == 404:
        return True
    print("  BLAD usuwania " + item_id + ": " + str(response.status_code) + " " + response.text[:200])
    return False


# --------------------------------------------------------------------------- #
# Stan synchronizacji: ktore elementy sa w Microsoft 365 i w jakiej wersji
# --------------------------------------------------------------------------- #
# Graph nie pozwala wylistowac elementow konektora, wiec zapamietujemy je lokalnie:
# - zadanie usuniete w Plane (albo z usunietego projektu) jest usuwane z Copilota,
# - zadanie, w ktorym nic sie nie zmienilo (tresc i uprawnienia), nie jest wysylane
#   ponownie - dzieki temu synchronizacje mozna uruchamiac czesto (np. co 30 minut).
# Raz na dobe wszystko jest wysylane od nowa. Plik zawiera tylko identyfikatory i skroty.
STATE_FILE = settings.STATE_DIR / "sync_state.json"
LOCK_FILE = settings.STATE_DIR / "sync.lock"
FULL_REFRESH_EVERY = timedelta(hours=24)
# Blokada starsza niz to uznawana jest za pozostalosc po przerwanym przebiegu.
STALE_LOCK_AFTER = timedelta(hours=3)
# Zabezpieczenie: jesli z jakiegos powodu (np. inny token API, ktory widzi mniej projektow)
# mialoby zniknac wiecej elementow niz ten prog, nic nie usuwamy bez --allow-mass-delete.
MASS_DELETE_MIN = 20
MASS_DELETE_SHARE = 0.3


def _load_state():
    """({id elementu w Graph: {"project": id projektu, "hash": skrot}}, czas ostatniej pelnej wysylki)."""
    if not STATE_FILE.exists():
        return {}, None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("UWAGA: nie udalo sie odczytac " + STATE_FILE.name + " - zaczynam od pustego stanu.")
        return {}, None
    if data.get("connection_id") not in (None, settings.GRAPH_CONNECTION_ID):
        print("UWAGA: " + STATE_FILE.name + " dotyczy innego connection - zaczynam od pustego stanu.")
        return {}, None
    items = {}
    for gid, value in (data.get("items") or {}).items():
        # starszy format: {id elementu: id projektu}
        items[gid] = value if isinstance(value, dict) else {"project": value, "hash": None}
    last_full = data.get("last_full_at")
    try:
        last_full = datetime.fromisoformat(last_full) if last_full else None
    except ValueError:
        last_full = None
    return items, last_full


def _save_state(items, last_full):
    data = {
        "connection_id": settings.GRAPH_CONNECTION_ID,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_full_at": last_full.isoformat(timespec="seconds") if last_full else None,
        "items": dict(sorted(items.items())),
    }
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _fingerprint(external_item):
    """Skrot tresci i uprawnien elementu - zmienia sie, gdy trzeba go wyslac ponownie."""
    payload = json.dumps(external_item, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@contextmanager
def _single_run():
    """Nie dopuszcza do dwoch synchronizacji naraz (np. gdy poprzednia trwa dluzej niz odstep harmonogramu)."""
    if LOCK_FILE.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(LOCK_FILE.stat().st_mtime, timezone.utc)
        if age > STALE_LOCK_AFTER:
            print("Usuwam stara blokade " + LOCK_FILE.name + " (z przerwanego przebiegu).")
            LOCK_FILE.unlink(missing_ok=True)
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield True
    finally:
        LOCK_FILE.unlink(missing_ok=True)


# Wlasciwosci, ktore musza byc w schemacie w Graph, zanim wyslemy elementy
# (dodane pozniej niz pierwotny schemat - patrz graph_connection.py).
REQUIRED_SCHEMA_PROPERTIES = {"iconUrl", "created", "projectUrl", "itemKey", "createdBy"}
MAX_CONSECUTIVE_ERRORS = 5


def schema_status():
    """
    Stan connection w Graph: ("ok", None), ("missing", [brakujace wlasciwosci])
    - schematu brak albo jest nieaktualny, mozna go utworzyc/zaktualizowac -
    albo ("error", komunikat) - Graph nie odpowiada lub odmawia.
    """
    url = GRAPH_BASE + "/external/connections/" + settings.GRAPH_CONNECTION_ID + "/schema"
    try:
        response = requests.get(url, headers=_headers(), timeout=60)
    except requests.exceptions.RequestException as e:
        return "error", "Graph nie odpowiada (" + type(e).__name__ + ") - sprobuj pozniej."

    if response.status_code >= 500:
        return "error", ("API konektorow Microsoft Graph zwraca blad " + str(response.status_code)
                         + " (awaria po stronie Microsoft) - sprobuj pozniej.")
    if response.status_code == 404:
        # nie ma jeszcze connection albo schematu
        return "missing", sorted(REQUIRED_SCHEMA_PROPERTIES | {"title", "url"})
    if response.status_code != 200:
        return "error", "Nie udalo sie odczytac schematu: " + str(response.status_code) + " " + response.text[:300]

    names = {p.get("name") for p in response.json().get("properties", [])}
    missing = sorted(REQUIRED_SCHEMA_PROPERTIES - names)
    return ("missing", missing) if missing else ("ok", None)


def _check_graph_ready():
    """Sprawdza PRZED synchronizacja, czy Graph odpowiada i czy schemat jest aktualny. Komunikat bledu albo None."""
    state, detail = schema_status()
    if state == "error":
        return detail
    if state == "missing":
        return ("W schemacie w Graph brakuje wlasciwosci: " + ", ".join(detail)
                + ". Najpierw uruchom: python graph_connection.py (aktualizacja schematu), potem synchronizacje.")
    return None


def run_sync(allow_mass_delete=False, full=False):
    """Zwraca kod wyjscia: 0 - wszystko w porzadku, 1 - przerwano albo byly bledy (do monitoringu)."""
    with _single_run() as acquired:
        if not acquired:
            print("Inna synchronizacja jeszcze trwa (" + LOCK_FILE.name + ") - pomijam ten przebieg.")
            return 0
        return _run_sync(allow_mass_delete, full)


def _run_sync(allow_mass_delete, full):
    started = datetime.now(timezone.utc)
    print("Start synchronizacji: " + started.isoformat(timespec="seconds"))
    if settings.DEFAULT_ACL_TYPE not in ACL_MODES:
        print("PRZERWANO - DEFAULT_ACL_TYPE musi byc jednym z: " + ", ".join(sorted(ACL_MODES)))
        return 1
    print("Tryb ACL: " + settings.DEFAULT_ACL_TYPE)

    problem = _check_graph_ready()
    if problem:
        print("PRZERWANO - " + problem)
        return 1

    previous, last_full = _load_state()
    full = full or last_full is None or started - last_full > FULL_REFRESH_EVERY
    print("Tryb: " + ("pelna wysylka wszystkich zadan" if full else "tylko zmienione zadania"))

    print("Pobieram liste projektow z Plane...")
    projects = list_projects()
    print("Znaleziono " + str(len(projects)) + " projekt(ow).")

    present = {}                  # elementy, ktore po tej synchronizacji sa w Graph
    unreadable_projects = set()   # projekty, ktorych nie udalo sie odczytac - ich elementow nie ruszamy
    hidden = set()                # zadania istniejace w Plane, ale bez nikogo uprawnionego (juz usuniete)
    total_synced = 0
    total_unchanged = 0
    total_failed = 0
    total_hidden = 0
    consecutive_errors = 0
    skipped_projects = []

    for project in projects:
        project_name = project.get("name", "?")
        print("")
        print("Projekt: " + project_name)

        try:
            access = ProjectAccess(project)
            work_items = list_all_work_items(project["id"])
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            print("  POMINIETO projekt (HTTP " + str(status) + " - brak dostepu tokena API do tego projektu)")
            skipped_projects.append(project_name + " (HTTP " + str(status) + ")")
            unreadable_projects.add(project["id"])
            continue

        print("  Zadan w projekcie: " + str(len(work_items)))

        for item in work_items:
            graph_id = project["id"] + "_" + item["id"]
            acl = access.acl_for(item)
            if not acl:
                # Graph nie przyjmie elementu bez ACL; usuwamy ewentualna stara kopie,
                # zeby nie zostala widoczna dla osob, ktore juz nie maja dostepu
                if graph_id in previous or full:
                    if not _remove_item(graph_id, "nikt z kontem w Entra ID nie ma do niego dostepu"):
                        present[graph_id] = {"project": project["id"], "hash": None}
                hidden.add(graph_id)
                total_hidden += 1
                continue
            external_item = _map_work_item_to_external_item(project, item, acl, access.creator_name(item))
            fingerprint = _fingerprint(external_item)
            if not full and (previous.get(graph_id) or {}).get("hash") == fingerprint:
                present[graph_id] = previous[graph_id]
                total_unchanged += 1
                continue
            if _push_item(external_item):
                present[graph_id] = {"project": project["id"], "hash": fingerprint}
                total_synced += 1
                consecutive_errors = 0
            else:
                # zadanie nadal jest w Plane - nie wolno go usunac; bez skrotu, zeby ponowic wysylke
                present[graph_id] = {"project": project["id"], "hash": None}
                total_failed += 1
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print("")
                    print("PRZERWANO - " + str(MAX_CONSECUTIVE_ERRORS) + " bledow zapisu z rzedu. "
                          "Zapisano " + str(total_synced) + " zadan. Sprawdz komunikaty powyzej i sprobuj pozniej.")
                    # nie usuwamy niczego, ale zapamietujemy wszystko, co znamy
                    _save_state({**previous, **present}, last_full)
                    return 1

    # Zadania, ktore byly w Microsoft 365, a nie ma ich juz w Plane (usuniete zadania,
    # usuniete projekty). Elementow z projektow, ktorych nie udalo sie odczytac, nie ruszamy.
    kept = {gid: entry for gid, entry in previous.items()
            if entry["project"] in unreadable_projects and gid not in present}
    gone = [gid for gid, entry in previous.items()
            if gid not in present and gid not in hidden and entry["project"] not in unreadable_projects]
    mass_delete_blocked = False
    print("")
    if gone and not allow_mass_delete and len(gone) > max(MASS_DELETE_MIN, MASS_DELETE_SHARE * len(previous)):
        print("UWAGA: z Plane zniknelo " + str(len(gone)) + " z " + str(len(previous))
              + " wczesniej wyslanych zadan - to podejrzanie duzo (inny token API? blad Plane?).")
        print("Niczego nie usunieto. Jesli to zamierzone, uruchom: python sync_service.py --allow-mass-delete")
        kept.update({gid: previous[gid] for gid in gone})
        mass_delete_blocked = True
    else:
        if gone:
            print("Usuwam z Copilota " + str(len(gone)) + " zadan, ktorych nie ma juz w Plane...")
        for gid in gone:
            if not _remove_item(gid, "usuniete w Plane"):
                kept[gid] = previous[gid]
    # pelna wysylka zaliczona tylko wtedy, gdy wszystko sie udalo
    clean = not total_failed and not unreadable_projects
    _save_state({**kept, **present}, started if full and clean else last_full)

    print("")
    print("Zakonczono. Wyslano " + str(total_synced) + " zadan, bez zmian: " + str(total_unchanged)
          + (", bledow: " + str(total_failed) if total_failed else "") + ".")
    if total_hidden:
        print("Pominieto " + str(total_hidden) + " zadan, ktorych w trybie '" + settings.DEFAULT_ACL_TYPE
              + "' nie widzi nikt z kontem w Entra ID (np. nieprzypisanych w projekcie bez lidera).")

    if skipped_projects:
        print("")
        print("UWAGA - pominieto " + str(len(skipped_projects)) + " projekt(ow) z powodu braku dostepu:")
        for name in skipped_projects:
            print("  - " + name)
        print("Sprawdz, czy token API to bot token z god-mode (widzi wszystkie projekty).")

    return 1 if (total_failed or skipped_projects or mass_delete_blocked) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronizacja zadan z Plane do Microsoft 365 (Copilot).")
    parser.add_argument("--full", action="store_true",
                        help="wyslij wszystkie zadania od nowa, takze niezmienione")
    parser.add_argument("--allow-mass-delete", action="store_true",
                        help="pozwol usunac z Copilota duzo zadan naraz (gdy naprawde zniknely z Plane)")
    args = parser.parse_args()
    sys.exit(run_sync(allow_mass_delete=args.allow_mass_delete, full=args.full))

