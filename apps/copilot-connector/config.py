# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Wczytuje konfiguracje ze zmiennych srodowiskowych (w kontenerze: z plane.env przez compose.yaml;
lokalnie: z pliku .env obok skryptow). Zadnych sekretow na sztywno w kodzie.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Lokalnie: plik .env obok skryptow. W kontenerze go nie ma - wartosci podaje compose.yaml.
load_dotenv(Path(__file__).with_name(".env"))


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _require(name: str) -> str:
    """Pobiera zmienna srodowiskowa i rzuca czytelny blad, jesli jej brakuje."""
    value = _env(name)
    if not value:
        raise RuntimeError(
            f"Brakuje zmiennej srodowiskowej '{name}'. "
            f"W kontenerze ustaw COPILOT_... w plane.env (patrz docs/copilot-connector.md), "
            f"lokalnie skopiuj .env.example -> .env i uzupelnij."
        )
    return value


class Settings:
    # Entra ID / Graph auth
    AZURE_TENANT_ID = _require("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = _require("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = _require("AZURE_CLIENT_SECRET")

    # Graph connection
    GRAPH_CONNECTION_ID = _env("GRAPH_CONNECTION_ID", "piplaneconnector")
    GRAPH_CONNECTION_NAME = _env("GRAPH_CONNECTION_NAME", "Pi-Plane Graph Connector")
    # Copilot wybiera zrodla danych do odpowiedzi m.in. na podstawie nazwy i opisu
    # connection, dlatego opis ma mowic: co to za tresc, jak ludzie ja nazywaja
    # i kiedy po nia siegaja (zalecenie Microsoft dla konektorow Copilota).
    GRAPH_CONNECTION_DESCRIPTION = _env(
        "GRAPH_CONNECTION_DESCRIPTION",
        "Zadania projektowe (work items, issues, tickety) z systemu Plane - firmowego "
        "narzedzia do zarzadzania projektami i zadaniami. Kazdy element to jedno zadanie: "
        "tytul, opis, status (np. Backlog, Todo, In Progress, Done), priorytet, osoby "
        "przypisane, projekt, terminy i data ostatniej zmiany. Uzywaj tego zrodla przy "
        "pytaniach o zadania w Plane, postep i stan projektow, kto nad czym pracuje, "
        "co jest do zrobienia, co jest w toku i co zostalo zakonczone.",
    )

    # Plane
    # Publiczny adres Plane - z niego budowane sa linki do zadan widoczne w Copilocie.
    PLANE_BASE_URL = _require("PLANE_BASE_URL").rstrip("/")
    # Adres, pod ktorym konektor wola API Plane. W stosie Pi-Plane to wewnetrzny http://api:8000
    # (bez wychodzenia przez proxy i bez certyfikatu); domyslnie ten sam co PLANE_BASE_URL.
    PLANE_API_URL = _env("PLANE_API_URL", PLANE_BASE_URL).rstrip("/")
    PLANE_WORKSPACE_SLUG = _require("PLANE_WORKSPACE_SLUG")
    PLANE_API_TOKEN = _require("PLANE_API_TOKEN")
    PLANE_SSL_CERT_PATH = _env("PLANE_SSL_CERT_PATH") or None
    # Ikona pokazywana przy wynikach z Plane (etykieta 'iconUrl'). Domyslnie ikona z samej
    # instancji Plane - mozna podac dowolny publiczny adres https.
    PLANE_ICON_URL = _env("PLANE_ICON_URL") or PLANE_BASE_URL + "/favicon/android-chrome-192x192.png"

    # precise  - zadanie widza tylko osoby do niego przypisane (wprost albo przez grupe),
    #            zadanie bez przypisanych osob - lider projektu,
    # project  - wszyscy czlonkowie projektu (jak w Plane),
    # everyone - wszyscy w firmie.
    DEFAULT_ACL_TYPE = _env("DEFAULT_ACL_TYPE", "precise").lower()

    # Gdzie trzymac stan synchronizacji (sync_state.json, sync.lock). W kontenerze: wolumen /data.
    STATE_DIR = Path(_env("STATE_DIR") or Path(__file__).parent)


settings = Settings()
