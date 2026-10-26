# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Which relation types a project lets people add.

``blocked_by`` and ``blocking`` are always available. The other types are grouped, and each group is switched on per
project with a flag on ``Project``. Switching a group off only stops new relations of those types: the ones that exist
stay in the database and stay visible.
"""

RELATION_TYPE_DISABLED = "relation_type_disabled"

# Project flag -> the relation names (both directions) it controls
RELATION_TOGGLE_GROUPS = {
    "is_relation_schedule_enabled": (
        "start_before",
        "start_after",
        "finish_before",
        "finish_after",
        "start_before_finish",
        "finish_after_start",
    ),
    "is_relation_traceability_enabled": (
        "implemented_by",
        "implements",
        "caused_by",
        "causes",
        "cloned_by",
        "clones",
        "tested_by",
        "tests",
    ),
    "is_relation_relates_to_enabled": ("relates_to",),
    "is_relation_duplicate_enabled": ("duplicate",),
}

RELATION_TOGGLE_BY_TYPE = {name: flag for flag, names in RELATION_TOGGLE_GROUPS.items() for name in names}
RELATION_TOGGLE_FLAGS = tuple(RELATION_TOGGLE_GROUPS)


def relation_type_enabled(project, relation_type):
    flag = RELATION_TOGGLE_BY_TYPE.get(relation_type)
    return flag is None or bool(getattr(project, flag))


def relation_type_disabled_error(project, relation_type):
    """An error payload when the project does not allow this relation type, else None."""
    if relation_type_enabled(project, relation_type):
        return None
    return {
        "error": f"The relation type {relation_type.replace('_', ' ')} is switched off in this project.",
        "error_code": RELATION_TYPE_DISABLED,
        "relation_type": relation_type,
    }
