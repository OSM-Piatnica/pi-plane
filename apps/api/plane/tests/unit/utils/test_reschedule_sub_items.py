# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sub-work items following a moved parent, and a parent's effective span: the parts that need no database.

1 June 2027 is a Tuesday, so 5 and 6 June are a weekend and 7 June is a Monday.
"""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest import mock

import pytest

from plane.utils import issue_reschedule
from plane.utils.issue_effective_span import EffectiveSpans, is_later, widen
from plane.utils.issue_hierarchy import IssueTree
from plane.utils.issue_reschedule import (
    DEPENDENT,
    SUB_ITEM,
    SUB_ITEMS_OFFER,
    ReschedulePlan,
    decide_reschedule,
    follow,
    start_offset,
)

WEEKEND = (0, 6)
CONFLICT = {"error": "Cannot update dates", "error_code": "relation_date_conflict"}


def day(number, month=6):
    return date(2027, month, number)


@pytest.mark.unit
class TestStartOffset:
    def test_counts_working_days_both_ways(self):
        # Friday 4 June to Tuesday 8 June is two working days later
        assert start_offset(day(4), day(8), WEEKEND) == 2
        assert start_offset(day(8), day(4), WEEKEND) == -2
        assert start_offset(day(4), day(4), WEEKEND) == 0

    def test_a_start_on_a_weekend_day_counts_as_the_next_working_day(self):
        # Saturday and Monday are the same working day
        assert start_offset(day(5), day(7), WEEKEND) == 0
        assert start_offset(day(4), day(6), WEEKEND) == 1

    def test_no_offset_without_both_starts(self):
        assert start_offset(None, day(8), WEEKEND) == 0
        assert start_offset(day(8), None, WEEKEND) == 0
        assert start_offset("2027-06-04", "2027-06-08", WEEKEND) == 2


@pytest.mark.unit
class TestFollow:
    def test_keeps_the_working_days_it_lasts(self):
        # Thursday 3 to Monday 7 June lasts three working days; two working days later it is Monday 7 to Wednesday 9
        assert follow({"start_date": day(3), "finish_date": day(7)}, 2, WEEKEND) == (day(7), day(9))

    def test_moves_earlier(self):
        assert follow({"start_date": day(7), "finish_date": day(9)}, -2, WEEKEND) == (day(3), day(7))

    def test_only_a_finish_date_moves_that(self):
        assert follow({"start_date": None, "finish_date": day(4)}, 1, WEEKEND) == (None, day(7))

    def test_only_a_start_date_moves_that(self):
        assert follow({"start_date": day(4), "finish_date": None}, 1, WEEKEND) == (day(7), None)

    def test_without_dates_nothing_moves(self):
        assert follow({"start_date": None, "finish_date": None}, 3, WEEKEND) is None


@pytest.mark.unit
class TestWiden:
    def test_the_roll_up_widens_own_dates_where_it_reaches_past_them(self):
        rollup = {"start_date": day(2), "target_date": day(18)}
        assert widen(day(4), day(10), rollup) == (day(2), day(18))
        assert widen(day(1), day(20), rollup) == (day(1), day(20))

    def test_without_a_roll_up_own_dates_stay(self):
        assert widen(day(4), day(10), None) == (day(4), day(10))

    def test_without_own_dates_the_roll_up_counts(self):
        assert widen(None, None, {"start_date": day(2), "target_date": day(18)}) == (day(2), day(18))
        assert widen(None, day(10), {"start_date": None, "target_date": None}) == (None, day(10))

    def test_is_later(self):
        assert is_later(day(5), day(4))
        assert is_later(day(5), None)
        assert not is_later(None, day(4))
        assert not is_later(day(4), day(4))


def node(issue_id, parent_id=None, start=None, finish=None):
    return {"id": issue_id, "parent_id": parent_id, "start_date": start, "finish_date": finish}


@pytest.mark.unit
class TestEffectiveSpans:
    @pytest.fixture
    def ids(self):
        return {name: uuid.uuid4() for name in ("parent", "child", "grandchild", "other")}

    @pytest.fixture
    def spans(self, ids):
        rows = [
            node(ids["parent"], None, day(1), day(10)),
            node(ids["child"], ids["parent"], day(3), day(8)),
            node(ids["grandchild"], ids["child"], day(4), day(9)),
            node(ids["other"], None, day(1), day(2)),
        ]
        with mock.patch.object(IssueTree, "for_project", side_effect=lambda *args, **kwargs: IssueTree(rows)):
            yield EffectiveSpans()

    def issue(self, ids, name, start, finish):
        return SimpleNamespace(id=ids[name], project_id="p", start_date=start, finish_date=finish)

    def test_a_parent_counts_with_its_own_dates_while_the_roll_up_stays_inside(self, ids, spans):
        parent = self.issue(ids, "parent", day(1), day(10))
        assert spans.span(parent) == {"start_date": day(1), "finish_date": day(10)}

    def test_a_planned_sub_item_widens_every_parent_above_it(self, ids, spans):
        parent = self.issue(ids, "parent", day(1), day(10))
        child = self.issue(ids, "child", day(3), day(8))
        spans.set_dates(ids["grandchild"], day(14), day(18))

        assert spans.span(parent) == {"start_date": day(1), "finish_date": day(18)}
        assert spans.span(child) == {"start_date": day(3), "finish_date": day(18)}
        # as saved, nothing reached past the parent
        assert spans.stored_span(parent) == {"start_date": day(1), "finish_date": day(10)}
        # and the planned dates are back afterwards
        assert spans.span(parent)["finish_date"] == day(18)

    def test_own_dates_can_be_given(self, ids, spans):
        parent = self.issue(ids, "parent", day(1), day(10))
        assert spans.span(parent, {"start_date": day(5), "finish_date": day(6)}) == {
            "start_date": day(3),
            "finish_date": day(9),
        }

    def test_ancestors_and_descendants(self, ids, spans):
        grandchild = self.issue(ids, "grandchild", day(4), day(9))
        parent = self.issue(ids, "parent", day(1), day(10))
        other = self.issue(ids, "other", day(1), day(2))
        assert spans.ancestors(grandchild) == [ids["child"], ids["parent"]]
        assert sorted(map(str, spans.descendants(parent))) == sorted([str(ids["child"]), str(ids["grandchild"])])
        assert spans.ancestors(other) == [] and spans.descendants(other) == []

    def test_own_dates_are_planned_or_saved(self, ids, spans):
        child = self.issue(ids, "child", day(3), day(8))
        assert spans.own_dates(child) == {"start_date": day(3), "finish_date": day(8)}
        spans.set_dates(str(ids["child"]), "2027-06-05", None)
        assert spans.own_dates(child) == {"start_date": day(5), "finish_date": None}


def fake_issue(name, start=None, finish=None, due=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        sequence_id=1,
        project=SimpleNamespace(identifier="SHF", weekend_days=[]),
        name=name,
        start_date=start,
        finish_date=finish,
        target_date=due,
    )


def plan(*entries):
    return ReschedulePlan(
        shifted={
            str(issue.id): {"issue": issue, "start_date": start, "finish_date": finish, "cause_id": "x", "kind": kind}
            for issue, start, finish, kind in entries
        }
    )


@pytest.mark.unit
class TestPayload:
    def test_without_sub_items_the_lists_stay_as_before(self):
        successor = fake_issue("successor", day(11), day(20))
        body = plan((successor, day(15), day(24), DEPENDENT)).payload(CONFLICT)

        assert body["error_code"] == "relation_reschedule_available"
        assert body["original_error_code"] == "relation_date_conflict"
        assert [shift["new_start_date"] for shift in body["shifts"]] == ["2027-06-15"]
        assert body["sub_items"] == []
        assert body["shifts_with_sub_items"] == body["shifts"]

    def test_with_sub_items_both_choices_are_listed(self):
        successor = fake_issue("successor", day(11), day(20))
        child = fake_issue("child", day(3), day(8))
        base = plan((successor, day(15), day(24), DEPENDENT))
        full = plan((successor, day(17), day(26), DEPENDENT), (child, day(7), day(12), SUB_ITEM))

        body = base.payload(CONFLICT, with_sub_items=full)

        assert [shift["new_start_date"] for shift in body["shifts"]] == ["2027-06-15"]
        assert [(shift["name"], shift["new_start_date"]) for shift in body["sub_items"]] == [("child", "2027-06-07")]
        assert [shift["new_start_date"] for shift in body["shifts_with_sub_items"]] == ["2027-06-17"]

    def test_a_sub_item_moved_past_its_due_date_carries_the_warning(self):
        # the fake project has no weekend days, so every day counts
        child = fake_issue("child", day(3), day(8), due=day(10))
        body = ReschedulePlan().payload(SUB_ITEMS_OFFER, with_sub_items=plan((child, day(7), day(12), SUB_ITEM)))

        [shift] = body["sub_items"]
        assert shift["target_date"] == "2027-06-10"
        assert (shift["deadline_overrun_days"], shift["previous_deadline_overrun_days"]) == (2, None)

    def test_an_offer_of_sub_items_alone_has_no_original_error(self):
        child = fake_issue("child", day(3), day(8))
        body = ReschedulePlan().payload(SUB_ITEMS_OFFER, with_sub_items=plan((child, day(7), day(12), SUB_ITEM)))

        assert body["original_error_code"] is None
        assert body["shifts"] == [] and body["shifts_with_sub_items"] == []
        assert len(body["sub_items"]) == 1


@pytest.mark.unit
class TestDecide:
    """Which plan a request gets, with the planner and the project setting stubbed out."""

    @pytest.fixture
    def issue(self):
        return fake_issue("parent", day(1), day(10))

    @pytest.fixture
    def plans(self, issue):
        successor = fake_issue("successor")
        child = fake_issue("child")
        return {
            False: plan((successor, day(15), day(24), DEPENDENT)),
            True: plan((successor, day(17), day(26), DEPENDENT), (child, day(7), day(12), SUB_ITEM)),
        }

    def decide(self, issue, plans, data, error=CONFLICT, enabled=True):
        def planner(proposed, issues_by_id, actor, with_sub_items=False):
            return plans.get(with_sub_items)

        proposed = {str(issue.id): {"start_date": day(5), "finish_date": day(14)}}
        with (
            mock.patch.object(issue_reschedule, "plan_reschedule", side_effect=planner) as planned,
            mock.patch.object(issue_reschedule, "is_offer_enabled", return_value=enabled),
        ):
            decision = decide_reschedule(proposed, {str(issue.id): issue}, None, error, data)
        return decision, planned

    def test_no_error_and_no_flag_queries_nothing(self, issue, plans):
        decision, planned = self.decide(issue, plans, {}, error=None)
        assert (decision.plan, decision.offer, decision.refusal) == (None, None, None)
        planned.assert_not_called()

    def test_another_error_is_refused(self, issue, plans):
        error = {"error": "status", "error_code": "relation_status_conflict"}
        decision, _ = self.decide(issue, plans, {"offer_sub_items": True}, error=error)
        assert decision.refusal == error

    def test_a_client_that_does_not_know_sub_items_gets_the_offer_as_before(self, issue, plans):
        decision, planned = self.decide(issue, plans, {})
        assert decision.offer["sub_items"] == []
        assert len(decision.offer["shifts"]) == 1
        # the plan with sub-items is not even worked out
        assert [call.kwargs.get("with_sub_items", False) for call in planned.call_args_list] == [False]

    def test_confirming_the_dependents_alone_leaves_the_sub_items(self, issue, plans):
        decision, _ = self.decide(issue, plans, {"shift_dependents": True})
        assert decision.plan is plans[False]

    def test_asked_the_offer_lists_the_sub_items(self, issue, plans):
        decision, _ = self.decide(issue, plans, {"offer_sub_items": True})
        assert len(decision.offer["sub_items"]) == 1
        assert decision.offer["shifts_with_sub_items"][0]["new_start_date"] == "2027-06-17"

    def test_asked_without_an_error_sub_items_alone_are_offered(self, issue, plans):
        plans[True] = plan((fake_issue("child"), day(7), day(12), SUB_ITEM))
        decision, _ = self.decide(issue, plans, {"offer_sub_items": True}, error=None)
        assert decision.offer["original_error_code"] is None
        assert decision.offer["shifts"] == []
        assert len(decision.offer["sub_items"]) == 1

    def test_asked_without_an_error_or_sub_items_it_is_saved(self, issue, plans):
        plans[True] = None
        decision, _ = self.decide(issue, plans, {"offer_sub_items": "true"}, error=None)
        assert (decision.plan, decision.offer, decision.refusal) == (None, None, None)

    def test_answered_yes(self, issue, plans):
        decision, _ = self.decide(issue, plans, {"shift_dependents": True, "move_sub_items": True})
        assert decision.plan is plans[True]

    def test_answered_no(self, issue, plans):
        decision, _ = self.decide(issue, plans, {"shift_dependents": True, "move_sub_items": False})
        assert decision.plan is plans[False]

    def test_answered_yes_without_confirming_the_dependents_is_offered_again(self, issue, plans):
        decision, _ = self.decide(issue, plans, {"move_sub_items": True})
        assert decision.plan is None and decision.offer is not None

    def test_answered_yes_with_only_sub_items_moving_needs_no_shift_confirmation(self, issue, plans):
        plans[True] = plan((fake_issue("child"), day(7), day(12), SUB_ITEM))
        decision, _ = self.decide(issue, plans, {"move_sub_items": True}, error=None)
        assert decision.plan is plans[True]

    def test_sub_items_that_can_no_longer_follow_stay(self, issue, plans):
        plans[True] = None
        decision, _ = self.decide(issue, plans, {"shift_dependents": True, "move_sub_items": True})
        assert decision.plan is plans[False]

    def test_a_dependent_that_cannot_move_refuses_the_change(self, issue, plans):
        plans[False] = None
        decision, _ = self.decide(issue, plans, {"offer_sub_items": True})
        assert decision.refusal == CONFLICT

    def test_switched_off_nothing_moves_along(self, issue, plans):
        refused, _ = self.decide(issue, plans, {"shift_dependents": True, "move_sub_items": True}, enabled=False)
        assert refused.refusal == CONFLICT
        saved, planned = self.decide(issue, plans, {"offer_sub_items": True}, error=None, enabled=False)
        assert (saved.plan, saved.offer, saved.refusal) == (None, None, None)
        planned.assert_not_called()
