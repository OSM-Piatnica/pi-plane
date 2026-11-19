# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Wyszukiwanie Object ID użytkowników Entra ID na podstawie ich adresu e-mail.

Dlaczego to potrzebne: ACL w Microsoft Graph wymaga Object ID (GUID) danej
osoby, a nie jej adresu e-mail. Żeby precyzyjnie odwzorować uprawnienia z Plane
(kto jest członkiem danego projektu), trzeba dla każdego adresu e-mail z Plane
znaleźć odpowiadający mu Object ID w Waszym tenancie.

Dokumentacja: https://learn.microsoft.com/en-us/graph/api/user-get

WAŻNE - dodatkowe uprawnienie: żeby to działało, aplikacja w Entra ID
potrzebuje jeszcze jednego uprawnienia typu Application: User.Read.All
(oprócz tych dwóch, które już macie). Bez tego wyszukiwanie użytkowników
zwróci błąd 403 Forbidden.
"""
import requests
from graph_auth import get_access_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Cache w pamięci - żeby nie odpytywać Graph API wielokrotnie o tę samą osobę
_email_to_object_id_cache: dict[str, str | None] = {}


def resolve_user_object_id(email: str) -> str | None:
    """
    Zwraca Object ID użytkownika Entra ID na podstawie adresu e-mail.
    Zwraca None, jeśli osoba nie istnieje w Entra ID (np. zewnętrzny kontraktor
    bez konta firmowego) - taką osobę pomijamy przy budowaniu ACL.
    """
    if not email:
        return None

    email = email.strip().lower()

    if email in _email_to_object_id_cache:
        return _email_to_object_id_cache[email]

    headers = {"Authorization": f"Bearer {get_access_token()}"}
    url = f"{GRAPH_BASE}/users/{email}"
    response = requests.get(url, headers=headers, params={"$select": "id,mail,userPrincipalName"}, timeout=60)

    if response.status_code == 200:
        object_id = response.json()["id"]
        _email_to_object_id_cache[email] = object_id
        return object_id

    if response.status_code == 404:
        print(f"Nie znaleziono w Entra ID użytkownika: {email} - zostanie pominięty")
        _email_to_object_id_cache[email] = None
        return None

    raise RuntimeError(f"Błąd wyszukiwania użytkownika {email}: {response.status_code} {response.text}")
