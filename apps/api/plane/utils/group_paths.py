# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Groups written as text: a nested group is its path from the top, "Parent / Child", like the web labels it.

A path is the way a file names a group, because a name alone is not unique below the top level.
"""

from plane.db.models import UserGroup

PATH_SEPARATOR = " / "


def group_paths(workspace_id) -> dict:
    """{group_id: "Parent / Child"} for every group of a workspace."""
    rows = {
        group_id: (name, parent_id)
        for group_id, name, parent_id in UserGroup.objects.filter(workspace_id=workspace_id).values_list(
            "id", "name", "parent_id"
        )
    }
    paths = {}
    for group_id in rows:
        names = []
        seen = set()
        current = group_id
        while current in rows and current not in seen:
            seen.add(current)
            name, current = rows[current]
            names.append(name)
        paths[group_id] = PATH_SEPARATOR.join(reversed(names))
    return paths


def _key(text) -> str:
    """A name or path as it is compared: case-insensitive, with the spaces around each separator ignored."""
    return "/".join(part.strip() for part in str(text).split("/")).strip().lower()


def index_groups(workspace_id) -> tuple[dict, dict]:
    """
    ({path: group_id}, {name: group_id or None}) of a workspace, keys lower-cased.

    The name index holds only names that are not ambiguous (None marks a name two groups share), so a plain
    name finds a nested group only when it cannot mean another.
    """
    by_path = {}
    by_name = {}
    for group_id, path in group_paths(workspace_id).items():
        by_path[_key(path)] = group_id
        name = _key(path.rsplit("/", 1)[-1])
        by_name[name] = None if name in by_name else group_id
    return by_path, by_name


def find_group(text, by_path: dict, by_name: dict):
    """The id of the group a file names by path or plain name, or None when it is unknown or ambiguous."""
    key = _key(text)
    if not key:
        return None
    return by_path.get(key) or by_name.get(key)
