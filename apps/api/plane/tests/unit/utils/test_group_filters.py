# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest

from plane.utils.group_filters import split_group_tokens


@pytest.mark.unit
class TestSplitGroupTokens:
    def test_ids_and_keywords_are_told_apart(self):
        first, second = uuid.uuid4(), uuid.uuid4()

        ids, my_groups, none = split_group_tokens(f"{first},my_groups,none,{second}")

        assert ids == {first, second}
        assert my_groups is True
        assert none is True

    def test_a_list_works_like_a_comma_separated_text(self):
        group = uuid.uuid4()

        assert split_group_tokens([str(group), "my_groups"]) == ({group}, True, False)

    def test_rubbish_blanks_and_null_are_ignored(self):
        assert split_group_tokens("null, ,not-a-uuid,") == (set(), False, False)

    def test_nothing_gives_nothing(self):
        assert split_group_tokens(None) == (set(), False, False)
        assert split_group_tokens("") == (set(), False, False)
