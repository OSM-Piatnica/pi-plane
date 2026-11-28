# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Proces uslugi copilot-connector w stosie Pi-Plane: co COPILOT_SYNC_INTERVAL_MINUTES minut
synchronizuje zadania z Plane do Microsoft 365 (Copilot).

Przed synchronizacja sprawdza connection i schemat w Microsoft Graph: gdy ich brak albo schemat
jest starszy niz kod (nowe wlasciwosci), sam je tworzy/aktualizuje (graph_connection.py).
Bledy jednego przebiegu (np. awaria Microsoft) nie zatrzymuja uslugi - kolejny przebieg
probuje ponownie. Konfiguracja: docs/copilot-connector.md.
"""
import os
import signal
import sys
import time
from datetime import datetime, timezone

DEFAULT_INTERVAL_MINUTES = 30
MIN_INTERVAL_MINUTES = 5
# Po bledzie konfiguracji (brak zmiennych) nie restartujemy w kolko - czekamy i konczymy.
CONFIG_ERROR_SLEEP_SECONDS = 600

_stopping = False


def _stop(signum, frame):
    global _stopping
    _stopping = True
    print("Otrzymano sygnal " + str(signum) + " - koncze po biezacym kroku.", flush=True)


def _interval_seconds():
    raw = (os.getenv("COPILOT_SYNC_INTERVAL_MINUTES") or "").strip()
    try:
        minutes = int(raw) if raw else DEFAULT_INTERVAL_MINUTES
    except ValueError:
        print("UWAGA: COPILOT_SYNC_INTERVAL_MINUTES='" + raw + "' nie jest liczba - uzywam "
              + str(DEFAULT_INTERVAL_MINUTES) + ".", flush=True)
        minutes = DEFAULT_INTERVAL_MINUTES
    return max(minutes, MIN_INTERVAL_MINUTES) * 60


def _sleep(seconds):
    """Czeka, ale reaguje na zatrzymanie uslugi (docker stop / stack rm)."""
    end = time.monotonic() + seconds
    while not _stopping and time.monotonic() < end:
        time.sleep(min(5, end - time.monotonic()))


def _ensure_graph_setup(sync_service, graph_connection):
    """True, gdy connection i schemat sa gotowe do synchronizacji."""
    state, detail = sync_service.schema_status()
    if state == "ok":
        return True
    if state == "error":
        print("Microsoft Graph: " + detail, flush=True)
        return False
    print("Microsoft Graph: brak connection albo nieaktualny schemat (" + ", ".join(detail)
          + ") - tworze/aktualizuje (rejestracja schematu trwa 5-15 minut).", flush=True)
    graph_connection.create_connection()
    graph_connection.create_schema()
    state, detail = sync_service.schema_status()
    if state != "ok":
        print("Schemat nadal nie jest gotowy (" + str(detail) + ") - sprobuje przy nastepnym przebiegu.", flush=True)
        return False
    return True


def run_once(sync_service, graph_connection):
    """Jeden przebieg: przygotowanie Graph i synchronizacja. Kod wyjscia jak w sync_service.run_sync."""
    try:
        if not _ensure_graph_setup(sync_service, graph_connection):
            return 1
        return sync_service.run_sync()
    except Exception as e:  # jeden nieudany przebieg nie moze zatrzymac uslugi
        print("BLAD przebiegu: " + type(e).__name__ + ": " + str(e)[:500], flush=True)
        return 1


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        import graph_connection
        import sync_service
    except RuntimeError as e:  # config.py: brakujace zmienne srodowiskowe
        print("BLAD konfiguracji: " + str(e), flush=True)
        _sleep(CONFIG_ERROR_SLEEP_SECONDS)
        return 1

    interval = _interval_seconds()
    print("copilot-connector: synchronizacja co " + str(interval // 60) + " min, tryb ACL "
          + sync_service.settings.DEFAULT_ACL_TYPE + ".", flush=True)
    while not _stopping:
        started = time.monotonic()
        print("=== " + datetime.now(timezone.utc).isoformat(timespec="seconds") + " ===", flush=True)
        code = run_once(sync_service, graph_connection)
        print("=== przebieg zakonczony, kod " + str(code) + " ===", flush=True)
        _sleep(max(0, interval - (time.monotonic() - started)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
