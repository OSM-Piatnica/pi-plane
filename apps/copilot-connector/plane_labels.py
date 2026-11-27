# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Tlumaczenia statusow i priorytetow - TAKIE SAME jak w interfejsie Plane
(wysylane do Copilota przy synchronizacji).

Skad: interfejs Plane trzyma tlumaczenia w plikach jezykowych (packages/i18n/locales/<jezyk>),
ktore przegladarka pobiera z serwera Plane jako pliki JavaScript. refresh_from_plane() pobiera
je z NASZEJ instancji (PLANE_BASE_URL) i zapisuje w plane_labels.json - dzieki temu w Copilocie
jest "Gotowe" dokladnie wtedy, gdy Plane pokazuje "Gotowe".

Jak Plane tlumaczy statusy (odtworzone 1:1 z kodu interfejsu):
  - nazwa stanu rowna jednej z domyslnych (Backlog, Todo, To do, In Progress, Done, Cancelled,
    Triage) -> tlumaczenie z 'common.default_state_names',
  - kazda inna (wlasna) nazwa stanu -> wyswietlana bez zmian, w kazdym jezyku.
Priorytety: 'work-item.priority' (urgent/high/medium/low), brak priorytetu: 'common.none'.

Jezyki dolaczane do danych: PLANE_LABEL_LANGUAGES - domyslnie "all", czyli kazdy jezyk interfejsu
Plane (mozna zawezic, np. "pl,en"). Copilot dostaje wszystkie i wybiera ten, w ktorym uzytkownik
napisal prompt.

Tlumaczenia wszystkich jezykow pobiera refresh_from_plane(); czego nie da sie odczytac, jest
w plane_labels_builtin.json (wygenerowane z packages/i18n/src/locales repozytorium Pi-Plane).
all_state_names() / all_priority_names() podaja nazwe we wszystkich jezykach naraz - "In corso",
"In Bearbeitung", "W trakcie" i "In Progress" to ten sam stan.

Reczne odswiezenie:  python plane_labels.py
"""
import json
import os
import re
import time
from pathlib import Path

# pobrane tlumaczenia leza w katalogu stanu (STATE_DIR, w kontenerze /data), dolaczone - obok kodu
LABELS_FILE = Path(os.getenv("STATE_DIR") or Path(__file__).parent) / "plane_labels.json"
BUILTIN_FILE = Path(__file__).with_name("plane_labels_builtin.json")
REFRESH_EVERY = 7 * 24 * 3600   # tlumaczenia zmieniaja sie tylko przy aktualizacji Plane

# Mapa z kodu interfejsu Plane: nazwa stanu -> klucz w default_state_names (wielkosc liter ma znaczenie).
DEFAULT_STATE_NAME_KEYS = {
    "Backlog": "backlog", "Todo": "todo", "To do": "todo", "In Progress": "in_progress",
    "Done": "done", "Cancelled": "cancelled", "Triage": "triage",
}
PRIORITY_KEYS = ("urgent", "high", "medium", "low", "none")

# Uzywane tylko, gdy nie udalo sie pobrac tlumaczen z Plane (wartosci z Plane 2.3.0).
_BUILTIN = {
    "pl": {"states": {"backlog": "Backlog", "todo": "Do zrobienia", "in_progress": "W trakcie", "done": "Gotowe",
                      "cancelled": "Anulowane", "triage": "Do kwalifikacji"},
           "priority": {"urgent": "Pilny", "high": "Wysoki", "medium": "Średni", "low": "Niski", "none": "Brak"}},
    "en": {"states": {"backlog": "Backlog", "todo": "To do", "in_progress": "In Progress", "done": "Done",
                      "cancelled": "Cancelled", "triage": "Triage"},
           "priority": {"urgent": "Urgent", "high": "High", "medium": "Medium", "low": "Low", "none": "None"}},
}


FIRST_LANGUAGES = ("pl", "en")


def languages():
    """Jezyki etykiet dla Copilota: PLANE_LABEL_LANGUAGES, np. "pl,en", albo "all" (domyslnie) - kazdy jezyk
    interfejsu Plane, polski i angielski na poczatku."""
    value = (os.getenv("PLANE_LABEL_LANGUAGES") or "all").strip()
    if value.lower() in ("all", "*"):
        rest = [lang for lang in all_languages() if lang not in FIRST_LANGUAGES]
        return list(FIRST_LANGUAGES) + rest
    return [lang.strip() for lang in value.split(",") if lang.strip()]


_builtin_cache = {}


def _builtin():
    """Tlumaczenia wszystkich jezykow Plane dolaczone do konektora (gdy pobranie z instancji sie nie uda)."""
    if "data" not in _builtin_cache:
        try:
            data = json.loads(BUILTIN_FILE.read_text(encoding="utf-8")).get("languages") or {}
        except (OSError, ValueError):
            data = {}
        _builtin_cache["data"] = {**data, **_BUILTIN}
    return _builtin_cache["data"]


_cache = {"mtime": None, "data": None}


def _load():
    try:
        mtime = LABELS_FILE.stat().st_mtime
    except OSError:
        return {"languages": _BUILTIN}
    if _cache["mtime"] != mtime:
        try:
            _cache["data"] = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache["data"] = {"languages": _BUILTIN}
        _cache["mtime"] = mtime
    return _cache["data"]


def _lang_table(lang):
    table = _load().get("languages", {}).get(lang) or _builtin().get(lang) or {}
    return table.get("states", {}), table.get("priority", {})


def _all_tables(lang):
    """Tlumaczenia jezyka z obu zrodel: pobrane z Plane i dolaczone do konektora."""
    for table in (_load().get("languages", {}).get(lang), _builtin().get(lang)):
        if table:
            yield table.get("states", {}), table.get("priority", {})


def all_languages():
    """Kazdy jezyk, ktory znamy: pobrany z Plane albo dolaczony do konektora."""
    return sorted(set(_load().get("languages", {})) | set(_builtin()))


def all_state_names(name):
    """Nazwa stanu we wszystkich jezykach Plane ('In Progress' -> 'W trakcie', 'In corso', 'In Bearbeitung'...).
    Wlasna (niedomyslna) nazwa stanu jest taka sama w kazdym jezyku."""
    names = {name or ""}
    key = DEFAULT_STATE_NAME_KEYS.get(name or "")
    if key:
        for lang in all_languages():
            for states, _ in _all_tables(lang):
                if states.get(key):
                    names.add(states[key])
    return {n for n in names if n}


def all_priority_names(priority):
    """Priorytet we wszystkich jezykach Plane ('high' -> 'Wysoki', 'Alta', 'Hoch', 'Haute'...)."""
    key = (priority or "none").lower()
    names = {key}
    for lang in all_languages():
        for _, priorities in _all_tables(lang):
            if priorities.get(key):
                names.add(priorities[key])
    return names


def state_labels(name, group=None):
    """{'pl': 'Gotowe', 'en': 'Done'} - tak jak pokazuje Plane; wlasne nazwy stanow bez zmian.
    ('group' zostal dla zgodnosci wywolan - Plane tlumaczy po nazwie, nie po grupie.)"""
    key = DEFAULT_STATE_NAME_KEYS.get(name or "")
    result = {}
    for lang in languages():
        states, _ = _lang_table(lang)
        result[lang] = states.get(key, name) if key else (name or "")
    return result


def priority_labels(priority):
    key = (priority or "none").lower()
    result = {}
    for lang in languages():
        _, priorities = _lang_table(lang)
        result[lang] = priorities.get(key, priority or "")
    return result


def bilingual(original, labels):
    """'In Progress (pl: W trakcie; it: In corso; de: In Bearbeitung; es,pt-BR: ...)' - jezyki o tej samej nazwie
    razem, nazwy takie jak oryginal pominiete; gdy tlumaczenia nic nie zmieniaja - sam oryginal."""
    groups = {}
    for lang, value in labels.items():
        if value and value != original:
            groups.setdefault(value, []).append(lang)
    if not groups:
        return original
    return original + " (" + "; ".join(",".join(langs) + ": " + value for value, langs in groups.items()) + ")"


# --------------------------------------------------------------------------- #
# Pobieranie tlumaczen z instancji Plane
# --------------------------------------------------------------------------- #

def _parse_object(text, start):
    """Paruje plaski obiekt {klucz:`wartosc`,...} zaczynajacy sie od indeksu 'start' (zminifikowany JS)."""
    end = text.index("}", start)
    return dict(re.findall(r"(\w+):`([^`]*)`", text[start:end + 1])) or None


def _named_object(text, key):
    """Wartosc klucza 'key' z pliku jezykowego - wpisana wprost (key:{...}) albo przez zmienna (key:aa ... aa={...})."""
    direct = re.search(r"(?<![\w$])" + key + r":\{", text)
    if direct:
        return _parse_object(text, direct.end() - 1)
    ref = re.search(r"(?<![\w$])" + key + r":([\w$]+)[,}]", text)
    if ref:
        definition = re.search(r"(?<![\w$.])" + re.escape(ref.group(1)) + r"=\{", text)
        if definition:
            return _parse_object(text, definition.end() - 1)
    return None


def refresh_from_plane(base_url, verify=True, langs=None, timeout=30):
    """Pobiera tlumaczenia z interfejsu Plane i zapisuje plane_labels.json. Zwraca slownik jezykow."""
    import requests

    session = requests.Session()
    session.verify = verify
    base_url = base_url.rstrip("/")
    index = session.get(base_url + "/", timeout=timeout).text
    chunks = re.findall(r"/assets/[\w.\-]+\.js", index)
    locale_map = None
    for chunk in dict.fromkeys(chunks):   # mapa "../locales/<jezyk>/<plik>.json" -> plik JS jest w jednym z nich
        body = session.get(base_url + chunk, timeout=timeout).text
        if "../locales/" in body and "/common.json" in body:
            locale_map = body
            break
    if locale_map is None:
        raise RuntimeError("Nie znaleziono plikow jezykowych w interfejsie Plane (inna wersja Plane?).")
    # wszystkie jezyki, ktore ma ta instancja Plane (do rozpoznawania), plus te pokazywane w Copilocie
    available = dict.fromkeys(re.findall(r'"\.\./locales/([\w\-]+)/common\.json"', locale_map))
    langs = list(dict.fromkeys(list(langs or available) + languages()))

    def chunk_for(lang, name):
        m = re.search(r'"\.\./locales/' + re.escape(lang) + "/" + name + r'\.json":\(\)=>\w+\(\(\)=>import\(`\./([\w.\-]+\.js)`',
                      locale_map)
        if not m:
            raise RuntimeError("Plane nie ma jezyka '" + lang + "' (" + name + ").")
        return session.get(base_url + "/assets/" + m.group(1), timeout=timeout).text

    def read(lang):
        common, work_item = chunk_for(lang, "common"), chunk_for(lang, "work-item")
        states = _named_object(common, "default_state_names") or {}
        priority = {k: v for k, v in (_named_object(work_item, "priority") or {}).items() if k in PRIORITY_KEYS}
        none = re.search(r"(?<![\w$.])none:`([^`]*)`", common)
        if none:
            priority["none"] = none.group(1)
        return {"states": states, "priority": priority}

    # Brakujace w danym jezyku klucze Plane pokazuje po angielsku - robimy tak samo.
    english = read("en")
    if not english["states"] or len(english["priority"]) < len(PRIORITY_KEYS):
        raise RuntimeError("Nie udalo sie odczytac angielskich tlumaczen z Plane (inna wersja Plane?).")
    result = {}
    for lang in langs:
        if lang == "en":
            table = english
        elif lang in available:
            table = read(lang)
        else:
            # tego jezyka nie ma ta instancja Plane - zostaja tlumaczenia dolaczone do konektora
            table = {"states": {}, "priority": {}}
        # czego nie udalo sie odczytac z plikow JS (inny uklad zminifikowanego kodu), bierzemy z tlumaczen
        # dolaczonych do konektora, a dopiero potem po angielsku - jak Plane
        builtin = _builtin().get(lang, {})
        result[lang] = {part: {**english[part], **builtin.get(part, {}), **table[part]}
                        for part in ("states", "priority")}

    tmp = LABELS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"source": base_url, "fetched_at": int(time.time()), "all_languages": True,
                               "languages": result},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(LABELS_FILE)
    return result


def ensure_fresh(base_url, verify=True):
    """Odswieza plane_labels.json, gdy go brak, jest starszy niz tydzien albo brakuje jezyka.
    Blad pobierania nie przerywa pracy - zostaja dotychczasowe (lub wbudowane) tlumaczenia."""
    data = _load()
    fresh = (data.get("fetched_at", 0) > time.time() - REFRESH_EVERY
             and data.get("all_languages")
             and all(lang in data.get("languages", {}) for lang in languages()))
    if fresh:
        return None
    try:
        refresh_from_plane(base_url, verify)
        return None
    except Exception as e:
        return "nie udalo sie pobrac tlumaczen z Plane (" + type(e).__name__ + ": " + str(e)[:150] + ")"


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    cert = os.getenv("PLANE_SSL_CERT_PATH")
    verify = str(Path(__file__).parent / cert) if cert and not Path(cert).is_absolute() else (cert or True)
    data = refresh_from_plane(os.environ["PLANE_BASE_URL"], verify)
    print("Zapisano " + LABELS_FILE.name + ":")
    print(json.dumps(data, ensure_ascii=False, indent=2))
