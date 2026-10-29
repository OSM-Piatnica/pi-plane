# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Choosing which parts of the work items a project copy carries."""

import pytest

from plane.utils.project_copy_work_items import (
    WORK_ITEM_PROPERTIES,
    WORK_ITEM_PROPERTY_GROUPS,
    InvalidWorkItemProperties,
    resolve_work_item_properties,
)


@pytest.mark.unit
class TestResolveWorkItemProperties:
    def test_no_choice_means_everything(self):
        assert resolve_work_item_properties(None) == list(WORK_ITEM_PROPERTIES)

    def test_the_groups_cover_every_property_once(self):
        grouped = [name for group in WORK_ITEM_PROPERTY_GROUPS.values() for name in group]
        assert len(grouped) == len(set(grouped))
        assert grouped == list(WORK_ITEM_PROPERTIES)

    def test_an_empty_choice_means_nothing(self):
        assert resolve_work_item_properties([]) == []

    def test_the_result_follows_the_order_of_the_options_not_of_the_request(self):
        assert resolve_work_item_properties(["links", "dates"]) == ["dates", "links"]

    def test_an_unknown_name_is_rejected_and_named(self):
        with pytest.raises(InvalidWorkItemProperties) as raised:
            resolve_work_item_properties(["dates", "bogus"])

        assert raised.value.unknown == ["bogus"]

    @pytest.mark.parametrize("value", ["dates", {"dates": True}, [1], [None]])
    def test_anything_but_a_list_of_names_is_rejected(self, value):
        with pytest.raises(InvalidWorkItemProperties):
            resolve_work_item_properties(value)

    @pytest.mark.parametrize("name", ["comments", "attachments", "worklogs", "subscribers", "history"])
    def test_other_peoples_words_files_and_hours_are_not_on_offer(self, name):
        assert name not in WORK_ITEM_PROPERTIES
