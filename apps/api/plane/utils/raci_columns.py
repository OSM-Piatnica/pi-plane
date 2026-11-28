# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
RACI in work item files: the ``RACI`` column of the export and the import, and ``O:XX`` labels.

A cell lists the roles of departments as ``letter:department`` entries separated by ";", for example
``O:RM;K:PR;Z:ZA``. The department is its code, or its name when it has no code; a ";" inside a name is written
"\\;". The letters are Polish (O, Z, K, I) or English (R, A, C, I); the import takes both, and the two sets mean
the same roles (I is "informed" in both). The export writes the letters of the language of the person who exports.

The Gantt-RACI prototype keeps roles as labels of the same form (``O:RM``). When RACI is on, an import turns such a
label into a role, if its department is known, instead of creating the label.
"""

import re

from plane.db.models import GroupKind, RaciRole, UserGroup

LETTER_ROLES = {
    # Polish: Odpowiada, Zatwierdza, Konsultowany, Informowany
    "O": RaciRole.RESPONSIBLE,
    "Z": RaciRole.APPROVER,
    "K": RaciRole.CONSULTED,
    # English: Responsible, Accountable (approver), Consulted, Informed
    "R": RaciRole.RESPONSIBLE,
    "A": RaciRole.APPROVER,
    "C": RaciRole.CONSULTED,
    "I": RaciRole.INFORMED,
}
ROLE_ORDER = (RaciRole.RESPONSIBLE, RaciRole.APPROVER, RaciRole.CONSULTED, RaciRole.INFORMED)
EXPORT_LETTERS = {
    "pl": {RaciRole.RESPONSIBLE: "O", RaciRole.APPROVER: "Z", RaciRole.CONSULTED: "K", RaciRole.INFORMED: "I"},
    "en": {RaciRole.RESPONSIBLE: "R", RaciRole.APPROVER: "A", RaciRole.CONSULTED: "C", RaciRole.INFORMED: "I"},
}

_ENTRY_PATTERN = re.compile(r"^\s*([A-Za-z])\s*:\s*(.*?)\s*$", re.DOTALL)
_SEPARATOR = re.compile(r"(?<!\\);|\r?\n")


def letters_for_language(language) -> str:
    """The set of letters for a language of the interface: Polish (and its variants) or English for the others."""
    return "pl" if str(language or "").lower().startswith("pl") else "en"


def escape_department(token) -> str:
    return str(token).replace(";", "\\;")


def format_raci_cell(entries, letters="en") -> str:
    """
    ``[(role, department token)]`` as the text of a cell, roles in the order R, A, C, I and departments in the order
    given within a role. Roles that are not RACI roles are left out.
    """
    table = EXPORT_LETTERS.get(letters, EXPORT_LETTERS["en"])
    order = {role: position for position, role in enumerate(ROLE_ORDER)}
    known = [(role, token) for role, token in entries if role in table and str(token).strip()]
    ranked = sorted(enumerate(known), key=lambda item: (order[item[1][0]], item[0]))
    return ";".join(f"{table[role]}:{escape_department(token)}" for _, (role, token) in ranked)


def parse_raci_entry(text):
    """``"O:RM"`` as ``(role, "RM")``, or ``None`` when the text is not a letter, a colon and a department."""
    match = _ENTRY_PATTERN.match(str(text))
    if not match:
        return None
    role = LETTER_ROLES.get(match.group(1).upper())
    department = match.group(2).replace("\\;", ";").strip()
    if role is None or not department:
        return None
    return role, department


def parse_raci_cell(value):
    """
    The entries of a RACI cell: ``([(role, department token)], [entries that could not be read])``.

    Takes the text of a cell or a list of entries (a JSON file may hold either).
    """
    if value in (None, ""):
        return [], []
    parts = value if isinstance(value, list) else _SEPARATOR.split(str(value))
    entries, unreadable = [], []
    for part in parts:
        text = str(part).strip()
        if not text:
            continue
        parsed = parse_raci_entry(text)
        if parsed is None:
            unreadable.append(text)
        else:
            entries.append(parsed)
    return entries, unreadable


class DepartmentIndex:
    """The departments of a workspace, found by code or by name, both without regard to case."""

    def __init__(self, workspace_id):
        self.by_code = {}
        self.by_name = {}
        for group in UserGroup.objects.filter(workspace_id=workspace_id, kind=GroupKind.DEPARTMENT).only(
            "id", "name", "code", "is_active"
        ):
            if group.code:
                self.by_code[group.code.strip().lower()] = group
            self.by_name.setdefault(group.name.strip().lower(), []).append(group)

    def find(self, token):
        """``(department, problem)``; ``problem`` is "unknown" or "ambiguous" when there is no one department."""
        key = str(token).strip().lower()
        if key in self.by_code:
            return self.by_code[key], None
        named = self.by_name.get(key, [])
        if len(named) == 1:
            return named[0], None
        return None, "ambiguous" if named else "unknown"


def department_token(group) -> str:
    """How a file names a department: its code, or its name when it has none."""
    return (group.code or "").strip() or group.name
