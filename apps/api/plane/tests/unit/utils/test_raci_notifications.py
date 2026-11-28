# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI notifications: the matrix, which events an activity stands for, and who hears about it."""

import pytest

from plane.utils.raci_notifications import (
    APPROVAL_DECIDED,
    APPROVAL_REQUESTED,
    COMMENT,
    COMPLETED,
    DEFAULT_MATRIX,
    EVENTS,
    NEW_VERSION,
    STATE_OR_DUE_DATE,
    RaciMatrixError,
    activity_events,
    clean_matrix,
    normalize_matrix,
    preview_events,
    recipients_for_activities,
    roles_for_events,
)

DONE = "done-state"
ISSUE = "issue-1"
RM, QA, PR, ZA = "rm", "qa", "pr", "za"


def is_done(state_id):
    return state_id == DONE


def act(id, field, verb="updated", new_identifier=None, issue=ISSUE):
    return {"id": id, "field": field, "verb": verb, "new_identifier": new_identifier, "issue_detail": {"id": issue}}


@pytest.mark.unit
class TestMatrix:
    def test_defaults_follow_spec_02(self):
        matrix = normalize_matrix({})

        assert list(matrix) == list(EVENTS)
        assert matrix[NEW_VERSION] == ["responsible", "consulted"]
        assert matrix[COMMENT] == ["responsible", "consulted"]
        assert matrix[APPROVAL_REQUESTED] == ["responsible", "approver"]
        assert matrix[APPROVAL_DECIDED] == ["responsible", "approver", "consulted"]
        assert matrix[COMPLETED] == ["responsible", "approver", "consulted", "informed"]
        assert matrix[STATE_OR_DUE_DATE] == ["responsible", "consulted", "informed"]

    def test_approval_request_reaches_responsible_and_approver_not_informed(self):
        roles = roles_for_events(normalize_matrix({}), (APPROVAL_REQUESTED,))

        assert roles == {"responsible", "approver"}

    def test_stored_events_override_defaults_and_rubbish_is_dropped(self):
        matrix = normalize_matrix(
            {COMMENT: ["informed", "bogus", "responsible"], "bogus": ["responsible"], NEW_VERSION: "x"}
        )

        assert matrix[COMMENT] == ["responsible", "informed"]
        assert "bogus" not in matrix
        assert matrix[NEW_VERSION] == list(DEFAULT_MATRIX[NEW_VERSION])

    def test_an_empty_list_tells_nobody(self):
        assert normalize_matrix({COMMENT: []})[COMMENT] == []

    @pytest.mark.parametrize(
        "data, code",
        [
            ([], "not_an_object"),
            ({"bogus": []}, "unknown_event"),
            ({COMMENT: "responsible"}, "not_a_list"),
            ({COMMENT: ["boss"]}, "unknown_role"),
        ],
    )
    def test_clean_refuses_with_fixed_texts(self, data, code):
        with pytest.raises(RaciMatrixError) as caught:
            clean_matrix(data)

        assert caught.value.code == code
        assert "boss" not in caught.value.public_message

    def test_clean_keeps_only_named_events_in_role_order(self):
        assert clean_matrix({COMMENT: ["informed", "approver"]}) == {COMMENT: ["approver", "informed"]}


@pytest.mark.unit
class TestActivityEvents:
    @pytest.mark.parametrize(
        "activity, events",
        [
            (act("1", "attachment", "created"), (NEW_VERSION,)),
            (act("1", "attachment", "deleted"), ()),
            (act("1", "comment", "created"), (COMMENT,)),
            (act("1", "comment", "updated"), ()),
            (act("1", "state", new_identifier="todo"), (STATE_OR_DUE_DATE,)),
            (act("1", "state", new_identifier=DONE), (COMPLETED, STATE_OR_DUE_DATE)),
            (act("1", "target_date"), (STATE_OR_DUE_DATE,)),
            (act("1", "finish_date"), ()),
            (act("1", "priority"), ()),
            (act("1", "description"), ()),
        ],
    )
    def test_events(self, activity, events):
        assert activity_events(activity, is_done) == events


@pytest.mark.unit
class TestRecipients:
    rows = [(RM, "responsible"), (QA, "consulted"), (PR, "informed"), (ZA, "approver")]
    members = {RM: {"ania", "both"}, QA: {"kuba"}, PR: {"piotr", "both"}, ZA: {"zosia"}}

    def recipients(self, activities, matrix=None, exclude=()):
        return recipients_for_activities(
            activities, ISSUE, self.rows, self.members, matrix or normalize_matrix({}), is_done, exclude
        )

    def test_comment_reaches_responsible_and_consulted(self):
        found = self.recipients([act("c", "comment", "created")])

        assert set(found) == {"ania", "both", "kuba"}

    def test_completion_reaches_every_role(self):
        found = self.recipients([act("s", "state", new_identifier=DONE)])

        assert set(found) == {"ania", "both", "kuba", "piotr", "zosia"}

    def test_each_person_gets_only_the_activities_of_their_roles(self):
        found = self.recipients([act("c", "comment", "created"), act("d", "target_date"), act("p", "priority")])

        assert found["kuba"] == {"c", "d"}
        assert found["piotr"] == {"d"}
        assert found["both"] == {"c", "d"}  # in two departments, told once per activity
        assert "zosia" not in found

    def test_a_person_in_several_departments_hears_when_any_qualifies(self):
        found = self.recipients(
            [act("c", "comment", "created")], matrix={**normalize_matrix({}), COMMENT: ["informed"]}
        )

        assert set(found) == {"piotr", "both"}

    def test_excluded_people_and_other_work_items_are_left_out(self):
        found = self.recipients(
            [act("c", "comment", "created"), act("x", "comment", "created", issue="other")], exclude=["ania"]
        )

        assert "ania" not in found
        assert found["kuba"] == {"c"}

    def test_preview_lists_departments_and_people_per_event(self):
        events = {entry["event"]: entry for entry in preview_events(normalize_matrix({}), self.rows, self.members)}

        assert [entry["group_id"] for entry in events[APPROVAL_REQUESTED]["departments"]] == [RM, ZA]
        assert events[APPROVAL_REQUESTED]["member_ids"] == ["ania", "both", "zosia"]
        assert events[COMMENT]["departments"][1] == {"group_id": QA, "role": "consulted", "member_count": 1}

    def test_preview_counts_a_department_without_people(self):
        events = preview_events(normalize_matrix({}), [("empty", "responsible")], {})

        assert events[0]["departments"] == [{"group_id": "empty", "role": "responsible", "member_count": 0}]
        assert events[0]["member_ids"] == []
