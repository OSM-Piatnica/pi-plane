# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
KROK 1 i KROK 2: Utworzenie external connection oraz zdefiniowanie schematu.

Dokumentacja Microsoft:
- Create externalConnection: https://learn.microsoft.com/en-us/graph/api/externalconnectors-external-post-connections
- Create or update schema:   https://learn.microsoft.com/en-us/graph/api/externalconnectors-externalconnection-patch-schema

W stosie Pi-Plane robi to sam scheduler.py, gdy connection albo aktualnego schematu brakuje.
Recznie: python graph_connection.py. Potem serwis synchronizujacy (sync_service.py) tylko
dodaje/aktualizuje/usuwa pojedyncze elementy (externalItem).
"""
import time
import requests
from config import settings
from graph_auth import get_access_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def create_connection() -> None:
    """
    KROK 1: Tworzy external connection - logiczny "kontener" na dane z Plane.
    Odpowiada za to uprawnienie: ExternalConnection.ReadWrite.OwnedBy
    """
    url = f"{GRAPH_BASE}/external/connections"
    body = {
        "id": settings.GRAPH_CONNECTION_ID,           # np. "piplaneconnector" - unikalne w tenancie
        "name": settings.GRAPH_CONNECTION_NAME,        # widoczne w Microsoft 365 admin center
        "description": settings.GRAPH_CONNECTION_DESCRIPTION,
        # Pozwala Microsoft 365 rozpoznac link do zadania Plane wklejony np. na Teams
        # i powiazac go z elementem konektora (zwieksza szanse pokazania w Copilocie).
        # UWAGA: activitySettings mozna ustawic TYLKO przy tworzeniu connection -
        # istniejacego connection nie da sie o to uzupelnic przez PATCH.
        "activitySettings": {
            "urlToItemResolvers": [{
                "@odata.type": "#microsoft.graph.externalConnectors.itemIdResolver",
                "urlMatchInfo": {
                    "baseUrls": [settings.PLANE_BASE_URL],
                    "urlPattern": "/" + settings.PLANE_WORKSPACE_SLUG
                                  + "/projects/(?<projectId>[^/]+)/issues/(?<issueId>[^/?#]+)",
                },
                "itemId": "{projectId}_{issueId}",   # ten sam format ID co w sync_service.py
                "priority": 1,
            }],
        },
    }

    response = requests.post(url, headers=_headers(), json=body, timeout=60)

    if response.status_code == 201:
        print(f"Connection '{settings.GRAPH_CONNECTION_ID}' utworzone.")
    elif response.status_code == 409:
        print(f"Connection '{settings.GRAPH_CONNECTION_ID}' już istnieje - aktualizuję nazwę i opis.")
        update_connection()
    else:
        raise RuntimeError(f"Błąd tworzenia connection: {response.status_code} {response.text[:500]}")


def update_connection() -> None:
    """
    Aktualizuje nazwę i opis istniejącego connection (PATCH). Copilot dobiera źródła
    danych do pytania m.in. po nazwie i opisie, więc ogólnikowy opis obniża szansę,
    że w ogóle sięgnie po zadania z Plane.
    """
    url = f"{GRAPH_BASE}/external/connections/{settings.GRAPH_CONNECTION_ID}"
    body = {
        "name": settings.GRAPH_CONNECTION_NAME,
        "description": settings.GRAPH_CONNECTION_DESCRIPTION,
    }
    response = requests.patch(url, headers=_headers(), json=body, timeout=60)
    if response.status_code in (200, 204):
        print("Nazwa i opis connection zaktualizowane.")
    else:
        raise RuntimeError(f"Błąd aktualizacji connection: {response.status_code} {response.text[:500]}")


def create_schema() -> None:
    """
    KROK 2: Definiuje, jakie pola z Plane będą wysyłane i jak Copilot ma je rozumieć.

    Kluczowe "labels" (etykiety semantyczne), które Copilot rozpoznaje specjalnie:
    - title            -> wyświetlane jako tytuł wyniku          (WYMAGANA przez Copilota)
    - url              -> link, w który można kliknąć            (WYMAGANA przez Copilota)
    - iconUrl          -> ikona źródła przy wyniku               (WYMAGANA przez Copilota)
    - lastModifiedDateTime -> używane do sortowania/rankingu "ostatnio zmienione"
    - createdDateTime  -> data utworzenia zadania
    - createdBy        -> kto utworzyl zadanie
    - authors          -> kto jest powiązany z elementem (tu: osoba przypisana)
    - containerName / containerUrl -> projekt, w którym leży zadanie

    Microsoft: "The iconUrl, title, and url labels must be applied for content
    to surface in Copilot" (learn.microsoft.com/graph/connecting-external-content-experiences).

    Funkcję można uruchamiać ponownie na istniejącym schemacie: dodawanie nowych
    właściwości i etykiet jest dozwolone (usuwanie i zmiana typu - nie). Po zmianie
    schematu trzeba ponownie puścić synchronizację (python sync_service.py).

    UWAGA: rejestracja schematu jest operacją ASYNCHRONICZNĄ - może zająć 5-15 minut.
    Graph zwraca 202 Accepted + URL w nagłówku "Location", pod którym można sprawdzić status.
    """
    url = f"{GRAPH_BASE}/external/connections/{settings.GRAPH_CONNECTION_ID}/schema"

    body = {
        "baseType": "microsoft.graph.externalItem",
        "properties": [
            {"name": "title", "type": "String", "isSearchable": "true",
             "isRetrievable": "true", "isQueryable": "true", "labels": ["title"]},

            {"name": "url", "type": "String", "isRetrievable": "true", "labels": ["url"]},

            {"name": "description", "type": "String", "isSearchable": "true",
             "isRetrievable": "true"},

            {"name": "status", "type": "String", "isQueryable": "true",
             "isRetrievable": "true", "isSearchable": "true"},

            {"name": "assignedTo", "type": "String", "isQueryable": "true",
             "isRetrievable": "true", "isSearchable": "true", "labels": ["authors"]},

            {"name": "projectName", "type": "String", "isQueryable": "true",
             "isRetrievable": "true", "isSearchable": "true", "labels": ["containerName"]},

            {"name": "lastModified", "type": "DateTime", "isRetrievable": "true",
             "isQueryable": "true", "labels": ["lastModifiedDateTime"]},

            {"name": "priority", "type": "String", "isRetrievable": "true",
             "isQueryable": "true"},

            # --- dodane pod wymagania Copilota ---
            {"name": "iconUrl", "type": "String", "isRetrievable": "true",
             "labels": ["iconUrl"]},

            {"name": "created", "type": "DateTime", "isRetrievable": "true",
             "isQueryable": "true", "labels": ["createdDateTime"]},

            {"name": "projectUrl", "type": "String", "isRetrievable": "true",
             "labels": ["containerUrl"]},

            # klucz zadania widoczny w Plane, np. PROJ-14
            {"name": "itemKey", "type": "String", "isQueryable": "true",
             "isRetrievable": "true", "isSearchable": "true"},

            # kto utworzyl zadanie
            {"name": "createdBy", "type": "String", "isQueryable": "true",
             "isRetrievable": "true", "isSearchable": "true", "labels": ["createdBy"]},
        ],
    }

    response = requests.patch(url, headers=_headers(), json=body, timeout=60)

    if response.status_code == 202:
        operation_url = response.headers.get("Location")
        print("Schemat wysłany do rejestracji (to potrwa 5-15 minut).")
        if operation_url:
            print(f"   Sprawdź status pod: {operation_url}")
        _poll_schema_status(operation_url)
    else:
        raise RuntimeError(f"Błąd rejestracji schematu: {response.status_code} {response.text[:500]}")


def _poll_schema_status(operation_url: str, max_wait_seconds: int = 900) -> None:
    """Odpytuje status operacji rejestracji schematu, aż będzie 'completed' albo upłynie czas."""
    if not operation_url:
        return

    waited = 0
    interval = 30
    while waited < max_wait_seconds:
        response = requests.get(operation_url, headers=_headers(), timeout=60)
        if response.status_code == 200:
            status = response.json().get("status")
            print(f"   Status schematu: {status}")
            if status == "completed":
                print("Schemat zarejestrowany poprawnie - można wgrywać dane (externalItem).")
                return
            if status == "failed":
                raise RuntimeError(f"Rejestracja schematu nie powiodła się: {response.json()}")
        time.sleep(interval)
        waited += interval

    print("⚠️  Upłynął limit czasu oczekiwania - sprawdź status ręcznie pod powyższym URL.")


if __name__ == "__main__":
    # Uruchom raz: `python graph_connection.py`
    create_connection()
    create_schema()
