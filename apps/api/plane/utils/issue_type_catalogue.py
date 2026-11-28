# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The catalogue of ready-made work item types: Task, Bug, Story, Change request and Milestone.

Each entry brings a name, an icon, a description, a description template (the HTML the create form puts into the
description of a new work item of the type) and suggested custom properties. The catalogue is written in English
and Polish; any other language gets the English text.

Adding an entry to a workspace never makes a second type of it:

- a `standard` entry is skipped when the workspace has a type with its name in any of the catalogue's languages;
- the Milestone entry is the workspace's system type of the `milestone` kind (`workspace_kind_type`), so it adopts
  the milestone type the workspace already has (and fills in its empty icon and template) instead of making
  another. `ensure_project_kind_type(project, "milestone")` then finds that same type.
"""

from django.db import transaction

from plane.db.models import IssueType, IssueTypeKind, IssueTypeProperty
from plane.utils.project_issue_types import workspace_kind_type

CATALOGUE_LANGUAGES = ("en", "pl")
DEFAULT_LANGUAGE = "en"

CREATED = "created"
EXISTS = "exists"
UPDATED = "updated"


def _icon(name, color, background_color):
    # The shape the logo validation of the type serializer accepts (#485): short texts only
    return {"in_use": "icon", "icon": {"name": name, "color": color, "background_color": background_color}}


def _text(title, description=""):
    return {"title": title, "property_type": "text", "description": description}


def _dropdown(title, options, description=""):
    return {
        "title": title,
        "property_type": "dropdown",
        "description": description,
        "options": list(options),
        "select_mode": "single",
    }


CATALOGUE = (
    {
        "key": "task",
        "kind": IssueTypeKind.STANDARD,
        # The type a workspace starts from: made the workspace's default type when it has none
        "is_default": True,
        "logo_props": _icon("check_circle", "#3F76FF", "#EBF1FF"),
        "text": {
            "en": {
                "name": "Task",
                "description": "A piece of work to be done.",
                "template": "<h3>Goal</h3><p></p><h3>Definition of done</h3><ul><li><p></p></li></ul>",
                "properties": [],
            },
            "pl": {
                "name": "Zadanie",
                "description": "Praca do wykonania.",
                "template": "<h3>Cel</h3><p></p><h3>Kryteria ukończenia</h3><ul><li><p></p></li></ul>",
                "properties": [],
            },
        },
    },
    {
        "key": "bug",
        "kind": IssueTypeKind.STANDARD,
        "logo_props": _icon("bug_report", "#DC3E42", "#FFF0EF"),
        "text": {
            "en": {
                "name": "Bug",
                "description": "Something that does not work as it should.",
                "template": "<h3>Expected result</h3><p></p><h3>Actual result</h3><p></p>",
                "properties": [
                    _dropdown("Severity", ("Critical", "Major", "Minor", "Trivial")),
                    _text("Environment", "Where it happens: system, version, browser"),
                    _text("Steps to reproduce"),
                ],
            },
            "pl": {
                "name": "Błąd",
                "description": "Coś, co nie działa tak, jak powinno.",
                "template": "<h3>Oczekiwany wynik</h3><p></p><h3>Faktyczny wynik</h3><p></p>",
                "properties": [
                    _dropdown("Waga", ("Krytyczna", "Poważna", "Drobna", "Kosmetyczna")),
                    _text("Środowisko", "Gdzie występuje: system, wersja, przeglądarka"),
                    _text("Kroki do odtworzenia"),
                ],
            },
        },
    },
    {
        "key": "story",
        "kind": IssueTypeKind.STANDARD,
        "logo_props": _icon("auto_stories", "#8E4EC6", "#F7EDFE"),
        "text": {
            "en": {
                "name": "Story",
                "description": "A need of a user, told from their side.",
                "template": (
                    "<p>As a …, I want …, so that ….</p><h3>Acceptance criteria</h3><ul><li><p></p></li></ul>"
                ),
                "properties": [],
            },
            "pl": {
                "name": "Historyjka",
                "description": "Potrzeba użytkownika opisana z jego perspektywy.",
                "template": "<p>Jako … chcę …, aby ….</p><h3>Kryteria akceptacji</h3><ul><li><p></p></li></ul>",
                "properties": [],
            },
        },
    },
    {
        "key": "change_request",
        "kind": IssueTypeKind.STANDARD,
        "logo_props": _icon("change_circle", "#F76B15", "#FFF1E7"),
        "text": {
            "en": {
                "name": "Change request",
                "description": "A request to change something agreed or already delivered.",
                "template": "<h3>Proposed change</h3><p></p><h3>Alternatives considered</h3><p></p>",
                "properties": [
                    _text("Reason", "Why the change is needed"),
                    _text("Impact", "What the change affects: scope, schedule, cost"),
                ],
            },
            "pl": {
                "name": "Wniosek o zmianę",
                "description": "Prośba o zmianę czegoś uzgodnionego lub już dostarczonego.",
                "template": "<h3>Proponowana zmiana</h3><p></p><h3>Rozważane alternatywy</h3><p></p>",
                "properties": [
                    _text("Powód", "Dlaczego zmiana jest potrzebna"),
                    _text("Wpływ", "Na co wpływa zmiana: zakres, harmonogram, koszt"),
                ],
            },
        },
    },
    {
        "key": "milestone",
        "kind": IssueTypeKind.MILESTONE,
        "logo_props": _icon("diamond", "#30A46C", "#E9F9EE"),
        "text": {
            "en": {
                "name": "Milestone",
                "description": "A point in the schedule. Start and finish are one day; the due date is its deadline.",
                "template": "<h3>What has to be true by this date</h3><ul><li><p></p></li></ul>",
                "properties": [],
            },
            "pl": {
                "name": "Kamień milowy",
                "description": "Punkt w harmonogramie. Początek i koniec to jeden dzień; termin jest jego terminem.",
                "template": "<h3>Co musi być spełnione do tego dnia</h3><ul><li><p></p></li></ul>",
                "properties": [],
            },
        },
    },
)

CATALOGUE_BY_KEY = {entry["key"]: entry for entry in CATALOGUE}
CATALOGUE_KEYS = tuple(CATALOGUE_BY_KEY)


def catalogue_language(language) -> str:
    """The catalogue language for a language code such as `pl` or `pl-PL`; English when there is no text in it."""

    code = str(language or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in CATALOGUE_LANGUAGES else DEFAULT_LANGUAGE


def entry_text(entry, language) -> dict:
    return entry["text"][catalogue_language(language)]


def _entry_names(entry) -> set:
    return {text["name"].lower() for text in entry["text"].values()}


def existing_type_for_entry(workspace_id, entry):
    """The workspace's type that stands for this entry, or None: the oldest active type of a system kind, or a type
    with the entry's name in any catalogue language."""

    if entry["kind"] != IssueTypeKind.STANDARD:
        return (
            IssueType.objects.filter(
                workspace_id=workspace_id, kind=entry["kind"], is_active=True, deleted_at__isnull=True
            )
            .order_by("created_at", "id")
            .first()
        )
    names = _entry_names(entry)
    for issue_type in IssueType.objects.filter(workspace_id=workspace_id, deleted_at__isnull=True).order_by(
        "created_at", "id"
    ):
        if issue_type.name.strip().lower() in names:
            return issue_type
    return None


def list_catalogue(workspace_id, language=DEFAULT_LANGUAGE) -> list:
    """Every entry in `language`, with the id of the workspace's type that already stands for it (or None)."""

    rows = []
    for entry in CATALOGUE:
        text = entry_text(entry, language)
        existing = existing_type_for_entry(workspace_id, entry)
        rows.append(
            {
                "key": entry["key"],
                "kind": str(entry["kind"]),
                "is_default": bool(entry.get("is_default")),
                "name": text["name"],
                "description": text["description"],
                "logo_props": entry["logo_props"],
                "description_template": text["template"],
                "properties": [dict(prop) for prop in text["properties"]],
                "existing_type_id": str(existing.id) if existing else None,
            }
        )
    return rows


def _add_properties(issue_type, properties, created_by_id=None) -> int:
    """Add the suggested properties the type does not have yet (by title); returns how many were added."""

    have = {
        title.lower()
        for title in IssueTypeProperty.objects.filter(issue_type=issue_type, deleted_at__isnull=True).values_list(
            "title", flat=True
        )
    }
    added = 0
    for prop in properties:
        if prop["title"].lower() in have:
            continue
        IssueTypeProperty.objects.create(
            workspace_id=issue_type.workspace_id,
            issue_type=issue_type,
            title=prop["title"],
            description=prop.get("description", ""),
            property_type=prop["property_type"],
            options=list(prop.get("options", [])),
            select_mode=prop.get("select_mode", "single"),
            created_by_id=created_by_id,
        )
        added += 1
    return added


def _add_system_kind_entry(workspace_id, entry, text, created_by_id):
    """The Milestone entry: the workspace's milestone type, made from the catalogue when there is none yet."""

    existing = existing_type_for_entry(workspace_id, entry)
    if existing is None:
        issue_type = workspace_kind_type(
            workspace_id,
            entry["kind"],
            created_by_id=created_by_id,
            name=text["name"],
            defaults={
                "description": text["description"],
                "logo_props": entry["logo_props"],
                "description_template": text["template"],
            },
        )
        # A type another request made while this one waited for the workspace lock is adopted below instead
        if issue_type.description_template == text["template"]:
            _add_properties(issue_type, text["properties"], created_by_id)
            return issue_type, CREATED
        existing = issue_type

    # Adopt the type the workspace has: fill in what an admin left empty, never overwrite what they set
    changed = []
    if not existing.logo_props:
        existing.logo_props = entry["logo_props"]
        changed.append("logo_props")
    if not (existing.description_template or "").strip():
        existing.description_template = text["template"]
        changed.append("description_template")
    if not (existing.description or "").strip():
        existing.description = text["description"]
        changed.append("description")
    if changed:
        existing.save(update_fields=[*changed, "updated_at"])
    added = _add_properties(existing, text["properties"], created_by_id)
    return existing, (UPDATED if changed or added else EXISTS)


def _add_standard_entry(workspace_id, entry, text, created_by_id):
    existing = existing_type_for_entry(workspace_id, entry)
    if existing is not None:
        return existing, EXISTS
    is_default = (
        bool(entry.get("is_default"))
        and not IssueType.objects.filter(workspace_id=workspace_id, is_default=True, deleted_at__isnull=True).exists()
    )
    issue_type = IssueType.objects.create(
        workspace_id=workspace_id,
        name=text["name"],
        description=text["description"],
        logo_props=entry["logo_props"],
        description_template=text["template"],
        kind=entry["kind"],
        is_default=is_default,
        created_by_id=created_by_id,
    )
    _add_properties(issue_type, text["properties"], created_by_id)
    return issue_type, CREATED


def add_catalogue_types(workspace_id, keys=None, *, language=DEFAULT_LANGUAGE, created_by_id=None) -> list:
    """Add the catalogue entries `keys` (every entry when None) to the workspace.

    Returns `(key, issue_type, status)` per entry in catalogue order: `created`, `exists` (the workspace already has
    the type; nothing changed) or `updated` (the workspace's milestone type got the catalogue's icon, template or
    properties where it had none). Raises `ValueError` for an unknown key. The types are not linked to any project.
    """

    wanted = CATALOGUE_KEYS if keys is None else tuple(dict.fromkeys(keys))
    unknown = [key for key in wanted if key not in CATALOGUE_BY_KEY]
    if unknown:
        raise ValueError(f"Unknown catalogue entries: {', '.join(sorted(map(str, unknown)))}")

    results = []
    with transaction.atomic():
        for key in CATALOGUE_KEYS:
            if key not in wanted:
                continue
            entry = CATALOGUE_BY_KEY[key]
            text = entry_text(entry, language)
            if entry["kind"] == IssueTypeKind.STANDARD:
                issue_type, status = _add_standard_entry(workspace_id, entry, text, created_by_id)
            else:
                issue_type, status = _add_system_kind_entry(workspace_id, entry, text, created_by_id)
            results.append((key, issue_type, status))
    return results
