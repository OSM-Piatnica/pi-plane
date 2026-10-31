# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Groups written as text: a nested group is its path from the top, "Parent / Child", like the web labels it.

A path is the way a file names a group, because a name alone is not unique below the top level.

A group name can hold a "/" itself, so in path text a literal "/" in a name is written "\\/" and a literal backslash
"\\\\". The separator between the names stays " / ". Reading splits only on a "/" that is not escaped and unescapes the
names; a backslash before any other character (or at the end) is just a backslash, so a hand-written "A \\ B" works.
Writing always escapes.
"""

import json

from plane.db.models import UserGroup

PATH_SEPARATOR = " / "


def escape_name(name) -> str:
    """A group name as it is written inside a path: "\\" becomes "\\\\" and "/" becomes "\\/"."""
    return str(name).replace("\\", "\\\\").replace("/", "\\/")


def split_path(text) -> list[str]:
    """
    The names of a path text, unescaped and trimmed: split on every "/" that is not escaped.

    "R&D\\/QA / Team" is ["R&D/QA", "Team"]; "A \\ B" is ["A \\ B"] (a backslash before anything but "\\" or "/"
    stays a backslash, as does a trailing one).
    """
    parts = []
    current = []
    chars = str(text)
    index = 0
    while index < len(chars):
        char = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if char == "\\" and following in ("\\", "/"):
            current.append(following)
            index += 2
            continue
        if char == "/":
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current).strip())
    return parts


def escape_list_entry(path) -> str:
    """
    A path as one entry of a column that lists groups: every "," in it is written "\\,", so a group name with a comma
    does not split into two when the column is read as comma separated text (an Excel cell is written that way).
    """
    return str(path).replace(",", "\\,")


def _split_list_text(text) -> list[str]:
    """
    Split a column of groups on every "," that is not escaped, and unescape the commas.

    A backslash pair ("\\\\") and a "\\/" stay as they are (they belong to the path text inside an entry), a
    "\\," becomes a literal comma, any other backslash is just a backslash.
    """
    entries = []
    current = []
    chars = str(text)
    index = 0
    while index < len(chars):
        char = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if char == "\\" and following == ",":
            current.append(",")
            index += 2
            continue
        if char == "\\" and following in ("\\", "/"):
            current.append(char + following)
            index += 2
            continue
        if char == ",":
            entries.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    entries.append("".join(current).strip())
    return [entry for entry in entries if entry]


def unescape_list_entry(text) -> str:
    """One entry of an already split list (a JSON list): "\\," is a comma again, the rest is left to the path reader."""
    chars = str(text)
    result = []
    index = 0
    while index < len(chars):
        char = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if char == "\\" and following == ",":
            result.append(",")
            index += 2
            continue
        if char == "\\" and following in ("\\", "/"):
            result.append(char + following)
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def split_group_list(value) -> list[str]:
    """
    The entries (path texts) of a column that lists groups: a JSON list ('["Sales", "Sales / Poland"]', what CSV and
    JSON exports hold), a real list, or comma separated text (what an Excel cell holds); a comma inside a name is
    written "\\,".
    """
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [entry for entry in (unescape_list_entry(item).strip() for item in value) if entry]
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            return [entry for entry in (unescape_list_entry(item).strip() for item in parsed) if entry]
    return _split_list_text(text)


def _chains(workspace_id) -> dict:
    """{group_id: [name of the top group, ..., own name]} for every group of a workspace."""
    rows = {
        group_id: (name, parent_id)
        for group_id, name, parent_id in UserGroup.objects.filter(workspace_id=workspace_id).values_list(
            "id", "name", "parent_id"
        )
    }
    chains = {}
    for group_id in rows:
        names = []
        seen = set()
        current = group_id
        while current in rows and current not in seen:
            seen.add(current)
            name, current = rows[current]
            names.append(name)
        chains[group_id] = list(reversed(names))
    return chains


def group_paths(workspace_id) -> dict:
    """{group_id: "Parent / Child"} for every group of a workspace, a "/" or "\\" inside a name escaped."""
    return {
        group_id: PATH_SEPARATOR.join(escape_name(name) for name in names)
        for group_id, names in _chains(workspace_id).items()
    }


def _name_key(name) -> str:
    return str(name).strip().lower()


def _key(text) -> str:
    """A path text as it is compared: case-insensitive, names trimmed, the separators normalised to "/"."""
    return "/".join(escape_name(_name_key(part)) for part in split_path(text))


def _name_candidates(text) -> list[str]:
    """The plain names a text can mean: its only name, and the whole text as one name ("R&D/QA")."""
    parts = split_path(text)
    candidates = [_name_key(parts[0])] if len(parts) == 1 else []
    raw = _name_key(text)
    if raw and raw not in candidates:
        candidates.append(raw)
    return [candidate for candidate in candidates if candidate]


def index_groups(workspace_id) -> tuple[dict, dict]:
    """
    ({path: group_id}, {name: group_id or None}) of a workspace, keys lower-cased.

    The path keys are the escaped paths ("sales/poland"), the name keys the raw names ("r&d/qa"). The name index
    holds only names that are not ambiguous (None marks a name two groups share), so a plain name finds a nested
    group only when it cannot mean another.
    """
    by_path = {}
    by_name = {}
    for group_id, names in _chains(workspace_id).items():
        by_path["/".join(escape_name(_name_key(name)) for name in names)] = group_id
        name = _name_key(names[-1])
        by_name[name] = None if name in by_name else group_id
    return by_path, by_name


def is_ambiguous(text, by_name: dict) -> bool:
    """True when a plain name is shared by several groups (so the file has to write the full path)."""
    return any(candidate in by_name and by_name[candidate] is None for candidate in _name_candidates(text))


def find_group(text, by_path: dict, by_name: dict):
    """
    The id of the group a file names, or None when it is unknown or ambiguous.

    A path is tried first, then (when the text is one name, or is the raw name of a group such as "R&D/QA") a
    plain name that only one group has.
    """
    if not str(text).strip():
        return None
    found = by_path.get(_key(text))
    if found:
        return found
    for candidate in _name_candidates(text):
        found = by_name.get(candidate)
        if found:
            return found
    return None
