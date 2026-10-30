# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Group paths as text: a "/" or a backslash inside a group name is escaped, the separator is " / "."""

import pytest

from plane.db.models import UserGroup
from plane.utils.csv_utils import sanitize_csv_value
from plane.utils.group_paths import (
    escape_name,
    find_group,
    group_paths,
    index_groups,
    is_ambiguous,
    split_path,
)


@pytest.mark.unit
class TestEscaping:
    @pytest.mark.parametrize(
        "name, written",
        [
            ("Sales", "Sales"),
            ("R&D/QA", "R&D\\/QA"),
            ("A \\ B", "A \\\\ B"),
            ("Trailing\\", "Trailing\\\\"),
            ("A / B", "A \\/ B"),
            ("\\/", "\\\\\\/"),
        ],
    )
    def test_a_name_is_escaped_and_read_back_unchanged(self, name, written):
        assert escape_name(name) == written
        assert split_path(written) == [name]

    def test_only_an_unescaped_slash_separates_and_spaces_around_it_are_optional(self):
        assert split_path("Sales / Poland") == ["Sales", "Poland"]
        assert split_path("Sales/Poland") == ["Sales", "Poland"]
        assert split_path("R&D\\/QA / Team") == ["R&D/QA", "Team"]
        assert split_path("A \\\\ / B") == ["A \\", "B"]

    def test_a_backslash_before_anything_else_or_at_the_end_is_a_backslash(self):
        assert split_path("A \\ B") == ["A \\ B"]
        assert split_path("Trailing\\") == ["Trailing\\"]

    def test_the_formula_guard_does_not_touch_a_backslash(self):
        for name in ("R&D/QA", "A \\ B", "Trailing\\"):
            written = escape_name(name)
            assert sanitize_csv_value(written) == written


def _index(*groups):
    """Indexes for [(id, name, parent_id)] built the way index_groups does, without a database."""
    from unittest import mock

    rows = list(groups)
    with mock.patch("plane.utils.group_paths.UserGroup") as model:
        model.objects.filter.return_value.values_list.return_value = rows
        return index_groups("workspace"), group_paths("workspace")


@pytest.mark.unit
class TestFinding:
    def test_names_with_slashes_and_backslashes_are_found_by_their_written_path_or_raw_name(self):
        (by_path, by_name), paths = _index(
            (1, "R&D/QA", None), (2, "A \\ B", None), (3, "Sales", None), (4, "Poland", 3), (5, "Team / X", 3)
        )
        assert paths[1] == "R&D\\/QA"
        assert paths[2] == "A \\\\ B"
        assert paths[4] == "Sales / Poland"
        assert paths[5] == "Sales / Team \\/ X"
        for text in ("R&D\\/QA", "R&D/QA", " r&d\\/qa ", "R&D/qa"):
            assert find_group(text, by_path, by_name) == 1
        for text in ("A \\\\ B", "A \\ B", "a \\\\ b"):
            assert find_group(text, by_path, by_name) == 2
        assert find_group("Sales / Poland", by_path, by_name) == 4
        assert find_group("sales/poland", by_path, by_name) == 4
        assert find_group("Poland", by_path, by_name) == 4
        assert find_group("Sales / Team \\/ X", by_path, by_name) == 5
        assert find_group("Team / X", by_path, by_name) == 5  # the raw name, as no path Team / X exists
        assert find_group("Team \\/ X", by_path, by_name) == 5
        assert find_group("", by_path, by_name) is None

    def test_a_shared_name_is_ambiguous_and_an_escaped_path_still_resolves(self):
        (by_path, by_name), _ = _index((1, "Sales", None), (2, "Support", None), (3, "Team/1", 1), (4, "Team/1", 2))
        assert find_group("Team/1", by_path, by_name) is None
        assert is_ambiguous("Team\\/1", by_name)
        assert find_group("Sales / Team\\/1", by_path, by_name) == 3
        assert find_group("Support / Team\\/1", by_path, by_name) == 4
        assert not is_ambiguous("Sales", by_name)

    def test_a_path_of_nested_groups_is_not_mistaken_for_a_top_level_group_with_a_slash(self):
        (by_path, by_name), _ = _index((1, "R&D", None), (2, "QA", 1), (3, "R&D/QA", None))
        assert find_group("R&D / QA", by_path, by_name) == 2
        assert find_group("R&D\\/QA", by_path, by_name) == 3


@pytest.mark.unit
@pytest.mark.django_db
def test_paths_read_from_the_database_round_trip(workspace):
    top = UserGroup.objects.create(workspace=workspace, name="R&D/QA")
    other = UserGroup.objects.create(workspace=workspace, name="A \\ B")
    child = UserGroup.objects.create(workspace=workspace, name="Back\\", parent=other)
    by_path, by_name = index_groups(workspace.id)
    for group in (top, other, child):
        assert find_group(group_paths(workspace.id)[group.id], by_path, by_name) == group.id
