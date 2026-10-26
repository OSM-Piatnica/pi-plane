# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The relation types between work items, in one place.

A relation is stored once, as a row ``issue -> related_issue`` with the *forward* type. The other side sees the
*reverse* name of the same row: ``A blocked_by B`` is also ``B blocking A``. ``relates_to`` and ``duplicate`` read the
same from both sides.
"""

# (forward, reverse): the forward name is the one stored in the database
DIRECTED_RELATIONS = (
    ("blocked_by", "blocking"),
    ("start_before", "start_after"),
    ("finish_before", "finish_after"),
    ("start_before_finish", "finish_after_start"),
    ("implemented_by", "implements"),
    ("caused_by", "causes"),
    ("cloned_by", "clones"),
    ("tested_by", "tests"),
)
SYMMETRIC_RELATIONS = ("relates_to", "duplicate")

STORED_RELATION_TYPES = tuple(forward for forward, _ in DIRECTED_RELATIONS) + SYMMETRIC_RELATIONS
# Every name a client may use, in the order the UI lists them
ALL_RELATION_NAMES = tuple(name for pair in DIRECTED_RELATIONS for name in pair) + SYMMETRIC_RELATIONS
# Names whose row is stored with the two work items swapped
MIRRORED_RELATIONS = frozenset(reverse for _, reverse in DIRECTED_RELATIONS)
FORWARD_RELATIONS = frozenset(forward for forward, _ in DIRECTED_RELATIONS)

INVERSE_RELATIONS = {
    **{forward: reverse for forward, reverse in DIRECTED_RELATIONS},
    **{reverse: forward for forward, reverse in DIRECTED_RELATIONS},
    **{name: name for name in SYMMETRIC_RELATIONS},
}


def is_symmetric(relation_type):
    return relation_type in SYMMETRIC_RELATIONS


def is_mirrored(relation_type):
    """True when the row for this name is stored the other way round (``blocking`` is stored as ``blocked_by``)."""
    return relation_type in MIRRORED_RELATIONS
