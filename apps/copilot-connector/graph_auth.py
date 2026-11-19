# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Logowanie do Microsoft Graph przy pomocy Client ID + Client Secret
(tzw. client credentials flow - aplikacja loguje się "sama za siebie",
bez udziału zalogowanego użytkownika - dokładnie to, czego potrzebujemy
do serwisu działającego w tle/na harmonogramie).

Biblioteka: msal (oficjalna biblioteka Microsoft Authentication Library dla Pythona)
"""
import msal
from config import settings

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def get_access_token() -> str:
    """Zwraca ważny token dostępu (Bearer token) do wywoływania Microsoft Graph API."""
    authority = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"

    app = msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=authority,
    )

    # Najpierw próbuje z cache (jeśli token jeszcze ważny), inaczej pobiera nowy
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)

    if "access_token" not in result:
        error = result.get("error")
        description = result.get("error_description")
        raise RuntimeError(
            f"Nie udało się zalogować do Microsoft Graph: {error} - {description}\n"
            f"Sprawdź: czy Client Secret nie wygasł, czy uprawnienia mają status 'Granted' "
            f"w Entra ID -> App registrations -> Pi-Plane Graph Connector -> API permissions."
        )

    return result["access_token"]


if __name__ == "__main__":
    # Szybki test: uruchom `python graph_auth.py`, żeby sprawdzić, czy logowanie działa
    token = get_access_token()
    print("Zalogowano poprawnie. Pierwsze 20 znaków tokena:", token[:20], "...")
