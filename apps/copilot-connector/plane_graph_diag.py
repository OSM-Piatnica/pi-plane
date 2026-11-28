#!/usr/bin/env python3
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Diagnostyka Graph connectora "piplaneconnector".

Sprawdza:
  1. stan connection (state, ewentualne błędy),
  2. schemat (flagi searchable/queryable/retrievable, semantic labels wymagane przez Copilota),
  3. wybrane elementy (externalItems): czy istnieją, czy mają content, jakie mają ACL,
  4. czy object ID wskazanego użytkownika (np. osoby testujacej) jest w ACL tych elementów.

Uwaga: Graph NIE ma endpointu do listowania elementów connectora,
więc ID elementów trzeba podać (takie same, jakie nadaje skrypt synchronizujący),
albo pobrać je z Plane opcją --from-plane (format <project_id>_<issue_id>, jak w sync_service.py).

Wymagane zmienne (z pliku .env lub środowiska):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET   (aplikacja "Pi-Plane Graph Connector")
  dla --from-plane dodatkowo: PLANE_BASE_URL, PLANE_WORKSPACE_SLUG, PLANE_API_TOKEN

Uprawnienia aplikacji (application):
  ExternalConnection.Read.All lub ExternalConnection.ReadWrite.OwnedBy
  ExternalItem.Read.All     lub ExternalItem.ReadWrite.OwnedBy
  User.Read.All             (opcjonalnie: do zamiany UPN -> object ID i sprawdzenia ID z ACL)

Przykłady:
  python plane_graph_diag.py --user jan.kowalski@example.com --items plane-123 plane-456
  python plane_graph_diag.py --user-id 11111111-2222-3333-4444-555555555555 --items-file ids.txt
  python plane_graph_diag.py --user jan.kowalski@example.com --from-plane --limit 3
  python plane_graph_diag.py --from-plane --project "Nazwa projektu" --limit 10
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.microsoft.com/v1.0"
CONNECTION_ID = os.getenv("GRAPH_CONNECTION_ID", "piplaneconnector")

# Semantic labels, które Copilot wykorzystuje. Microsoft: "The iconUrl, title, and url
# labels must be applied for content to surface in Copilot".
REQUIRED_LABELS = {"title", "url", "iconUrl"}
RECOMMENDED_LABELS = {"lastModifiedDateTime", "createdBy", "lastModifiedBy", "createdDateTime"}

OK, WARN, ERR = "[OK]  ", "[UWAGA]", "[BŁĄD]"


def get_token() -> str:
    missing = [v for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET") if not os.environ.get(v)]
    if missing:
        sys.exit(f"{ERR} Brak zmiennych środowiskowych (.env): {', '.join(missing)}")
    r = requests.post(
        f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["AZURE_CLIENT_ID"],
            "client_secret": os.environ["AZURE_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    if r.status_code != 200:
        sys.exit(f"{ERR} Nie udało się pobrać tokena: {r.status_code} {r.text}")
    return r.json()["access_token"]


class Graph:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        # Bez tego v1.0 zwraca nowsze etykiety (iconUrl, containerName, containerUrl) jako 'unknownFutureValue'.
        self.s.headers["Prefer"] = "include-unknown-enum-members"

    def get(self, path: str):
        r = self.s.get(f"{GRAPH}{path}", timeout=30)
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text}
        return r.status_code, body


def err_msg(body) -> str:
    return body.get("error", {}).get("message", json.dumps(body)[:300]) if isinstance(body, dict) else str(body)


def check_connection(g: Graph) -> bool:
    print("\n=== 1. Connection ===")
    code, body = g.get(f"/external/connections/{CONNECTION_ID}")
    if code != 200:
        print(f"{ERR} GET connection: {code} {err_msg(body)}")
        return False
    state = body.get("state")
    print(f"{OK if state == 'ready' else WARN} state = {state}")
    print(f"       name = {body.get('name')}")
    if body.get("activitySettings"):
        print(f"       activitySettings = {json.dumps(body['activitySettings'])}")
    return True


def check_schema(g: Graph) -> set:
    print("\n=== 2. Schemat ===")
    code, body = g.get(f"/external/connections/{CONNECTION_ID}/schema")
    if code != 200:
        print(f"{ERR} GET schema: {code} {err_msg(body)}")
        return set()

    labels_found = set()
    for p in body.get("properties", []):
        flags = [f for f in ("isSearchable", "isQueryable", "isRetrievable", "isRefinable") if p.get(f)]
        labels = p.get("labels") or []
        labels_found.update(labels)
        line = f"       {p['name']:<28} {p['type']:<14} {','.join(flags) or '-'}"
        if labels:
            line += f"  labels={labels}"
        print(line)
        if not p.get("isRetrievable"):
            print(f"{WARN} '{p['name']}' nie jest retrievable – Copilot nie zobaczy tej wartości.")

    missing_req = REQUIRED_LABELS - labels_found
    missing_rec = RECOMMENDED_LABELS - labels_found
    if missing_req:
        print(f"{ERR} Brak wymaganych semantic labels: {sorted(missing_req)} – Copilot może ignorować dane.")
    else:
        print(f"{OK} Wymagane labels (title, url, iconUrl) są ustawione.")
    if missing_rec:
        print(f"{WARN} Brak zalecanych labels: {sorted(missing_rec)}")
    return labels_found


def resolve_user(g: Graph, upn: str) -> str | None:
    code, body = g.get(f"/users/{upn}?$select=id,displayName,userPrincipalName,mail")
    if code != 200:
        print(f"{ERR} Nie udało się pobrać użytkownika {upn}: {code} {err_msg(body)}")
        print("       (brak User.Read.All? Podaj object ID ręcznie przez --user-id)")
        return None
    print(f"{OK} {body.get('displayName')} | UPN={body.get('userPrincipalName')} | mail={body.get('mail')}")
    print(f"       object ID = {body['id']}")
    return body["id"]


def items_from_plane(limit: int, project_filter: str | None) -> list[str]:
    """Buduje ID elementów tak samo jak sync_service.py: <project_id>_<issue_id>."""
    print("\n=== 0. Pobieranie ID elementów z Plane ===")
    from plane_client import list_projects, list_work_items  # wymaga zmiennych PLANE_* w .env

    ids: list[str] = []
    try:
        projects = list_projects()
    except requests.exceptions.RequestException as e:
        sys.exit(f"{ERR} Nie udało się pobrać projektów z Plane: {e}")

    if project_filter:
        projects = [p for p in projects if project_filter.lower() in (p.get("name") or "").lower()]
        if not projects:
            sys.exit(f"{ERR} Brak projektu pasującego do '{project_filter}'.")

    for project in projects:
        name = project.get("name", "?")
        try:
            page = list_work_items(project["id"])
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            print(f"{WARN} {name}: pominięto (HTTP {status})")
            continue
        items = page.get("results", [])[:limit]
        print(f"       {name}: {len(items)} element(ów)")
        for item in items:
            print(f"         {project['id']}_{item['id']}  {item.get('name', '')[:60]}")
            ids.append(f"{project['id']}_{item['id']}")

    if not ids:
        sys.exit(f"{ERR} Nie znaleziono żadnych zadań w Plane.")
    return ids


def check_items(g: Graph, item_ids: list[str], user_id: str | None, verify_acl_ids: bool):
    print("\n=== 3. Elementy i ACL ===")
    summary = {"exists": 0, "missing": 0, "user_has_access": 0, "everyone": 0}
    seen_acl_ids: set[str] = set()

    for item_id in item_ids:
        print(f"\n--- {item_id}")
        code, body = g.get(f"/external/connections/{CONNECTION_ID}/items/{item_id}")
        if code == 404:
            print(f"{ERR} Element nie istnieje w Graph (404). Sprawdź format ID w skrypcie synchronizującym.")
            summary["missing"] += 1
            continue
        if code != 200:
            print(f"{ERR} {code} {err_msg(body)}")
            continue
        summary["exists"] += 1

        props = body.get("properties", {})
        title = props.get("title") or props.get("name") or "(brak tytułu)"
        print(f"       tytuł: {title}")
        print(f"       właściwości: {', '.join(k for k in props if not k.endswith('@odata.type'))}")

        content = (body.get("content") or {}).get("value", "")
        if content:
            print(f"{OK} content: {len(content)} znaków")
        else:
            print(f"{WARN} Brak content – Copilot ma mało tekstu do dopasowania.")

        acl = body.get("acl", [])
        if not acl:
            print(f"{ERR} Pusta ACL – nikt nie zobaczy elementu.")
        has_access = False
        for entry in acl:
            print(f"       ACL: {entry.get('accessType'):<5} {entry.get('type'):<14} {entry.get('value')}")
            if entry.get("type") == "everyone" and entry.get("accessType") == "grant":
                has_access = True
                summary["everyone"] += 1
            if entry.get("type") == "user":
                seen_acl_ids.add(entry.get("value", ""))
                if user_id and entry.get("value", "").lower() == user_id.lower():
                    has_access = entry.get("accessType") == "grant"
            if entry.get("type") in ("group", "externalGroup"):
                print(f"{WARN} Wpis typu {entry['type']} – członkostwo trzeba sprawdzić osobno.")

        if user_id:
            if has_access:
                print(f"{OK} Użytkownik ma dostęp do elementu.")
                summary["user_has_access"] += 1
            else:
                print(f"{ERR} Object ID użytkownika NIE występuje w ACL.")

    # Czy wartości z ACL to prawdziwe object ID z Entra?
    if verify_acl_ids and seen_acl_ids:
        print("\n=== 4. Weryfikacja ID z ACL w Entra ===")
        for uid in sorted(seen_acl_ids):
            code, body = g.get(f"/users/{uid}?$select=displayName,userPrincipalName")
            if code == 200:
                print(f"{OK} {uid} -> {body.get('displayName')} ({body.get('userPrincipalName')})")
            elif code == 404:
                print(f"{ERR} {uid} nie jest użytkownikiem w Entra (to e-mail? ID z Plane?).")
            else:
                print(f"{WARN} {uid}: {code} {err_msg(body)}")
                break  # najpewniej brak uprawnień – nie spamujemy

    print("\n=== Podsumowanie ===")
    print(f"       sprawdzono: {len(item_ids)}, istnieje: {summary['exists']}, brak: {summary['missing']}")
    if user_id:
        print(f"       użytkownik ma dostęp do: {summary['user_has_access']} z {summary['exists']}")
    if summary["everyone"]:
        print(f"       z ACL 'everyone': {summary['everyone']}")


def main():
    ap = argparse.ArgumentParser(description="Diagnostyka Graph connectora piplaneconnector")
    who = ap.add_mutually_exclusive_group()
    who.add_argument("--user", help="UPN/e-mail użytkownika (np. osoby testujacej) – zamieniany na object ID")
    who.add_argument("--user-id", help="Object ID użytkownika z Entra (gdy brak User.Read.All)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--items", nargs="+", help="ID elementów w Graph")
    src.add_argument("--items-file", help="Plik z ID elementów, jedno na linię")
    src.add_argument("--from-plane", action="store_true", help="Pobierz ID elementów z Plane (jak sync_service.py)")
    ap.add_argument("--limit", type=int, default=3, help="Ile zadań na projekt przy --from-plane (domyślnie 3)")
    ap.add_argument("--project", help="Przy --from-plane: tylko projekty, których nazwa zawiera ten tekst")
    ap.add_argument("--no-verify-acl", action="store_true", help="Nie sprawdzaj ID z ACL w Entra")
    args = ap.parse_args()

    if args.from_plane:
        item_ids = items_from_plane(args.limit, args.project)
    elif args.items:
        item_ids = args.items
    else:
        item_ids = [line.strip() for line in open(args.items_file, encoding="utf-8") if line.strip()]

    g = Graph(get_token())
    if not check_connection(g):
        sys.exit(1)
    check_schema(g)

    user_id = args.user_id
    if args.user:
        print("\n=== Użytkownik ===")
        user_id = resolve_user(g, args.user)

    check_items(g, item_ids, user_id, verify_acl_ids=not args.no_verify_acl)


if __name__ == "__main__":
    main()
