# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models.issue import IssueRelationChoices
from plane.utils.issue_relation_mapper import get_actual_relation, get_inverse_relation
from plane.utils.issue_relation_types import (
    ALL_RELATION_NAMES,
    DIRECTED_RELATIONS,
    MIRRORED_RELATIONS,
    STORED_RELATION_TYPES,
    SYMMETRIC_RELATIONS,
)

NEW_PAIRS = [("implemented_by", "implements"), ("caused_by", "causes"), ("cloned_by", "clones"), ("tested_by", "tests")]


@pytest.mark.unit
class TestRelationTypes:
    @pytest.mark.parametrize("forward, reverse", NEW_PAIRS)
    def test_new_types_are_pairs_stored_under_the_forward_name(self, forward, reverse):
        assert (forward, reverse) in DIRECTED_RELATIONS
        assert get_inverse_relation(forward) == reverse
        assert get_inverse_relation(reverse) == forward
        assert get_actual_relation(forward) == forward
        assert get_actual_relation(reverse) == forward

    def test_every_name_is_known_once(self):
        assert (
            len(ALL_RELATION_NAMES)
            == len(set(ALL_RELATION_NAMES))
            == 2 * len(DIRECTED_RELATIONS) + len(SYMMETRIC_RELATIONS)
        )

    def test_the_inverse_of_the_inverse_is_the_name_itself(self):
        for name in ALL_RELATION_NAMES:
            assert get_inverse_relation(get_inverse_relation(name)) == name

    def test_a_row_is_always_stored_under_a_stored_name(self):
        for name in ALL_RELATION_NAMES:
            assert get_actual_relation(name) in STORED_RELATION_TYPES

    def test_only_the_reverse_names_are_mirrored(self):
        assert MIRRORED_RELATIONS == {reverse for _, reverse in DIRECTED_RELATIONS}

    def test_the_model_knows_the_same_pairs(self):
        assert dict(IssueRelationChoices._RELATION_PAIRS) == {
            **dict(DIRECTED_RELATIONS),
            **{name: name for name in SYMMETRIC_RELATIONS},
        }
        for forward, _ in DIRECTED_RELATIONS:
            assert forward in IssueRelationChoices.values
