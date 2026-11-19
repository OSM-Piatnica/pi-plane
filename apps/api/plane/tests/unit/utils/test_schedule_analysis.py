# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Critical path analysis on networks small enough to compute by hand.

All dates are in June and July 2027: 1 June is a Tuesday, so the Mondays are 7, 14, 21 and 28 June and 5 July.
"""

from datetime import date

import pytest

from plane.utils.schedule_analysis import analyse_schedule, serialize_analysis

WEEKEND = (0, 6)


def day(text):
    """``"6-07"`` is 7 June 2027."""
    month, number = text.split("-")
    return date(2027, int(month), int(number))


def item(id, start=None, finish=None, due=None, group="started"):
    return {
        "id": id,
        "start_date": day(start) if start else None,
        "finish_date": day(finish) if finish else None,
        "target_date": day(due) if due else None,
        "state_group": group,
    }


def blocked_by(issue, blocker, lag=0):
    return (issue, blocker, "blocked_by", lag)


def analyse(items, relations=(), weekend_days=WEEKEND):
    return analyse_schedule(items, relations, weekend_days)


def dates_of(result, id):
    entry = result["items"][id]
    return tuple(
        entry[key].strftime("%-m-%d") for key in ("earliest_start", "earliest_finish", "latest_start", "latest_finish")
    )


def floats(result):
    return {id: entry["total_float"] for id, entry in result["items"].items()}


@pytest.mark.unit
class TestFinishToStart:
    def test_a_chain_shorter_than_the_longest_work_item_has_float(self):
        # A (3 days) then B (2 days) end on 11 June; C runs alone until 18 June and sets the end
        result = analyse(
            [item("A", "6-07", "6-09"), item("B", "6-10", "6-11"), item("C", "6-07", "6-18")],
            [blocked_by("B", "A")],
        )
        assert result["project_start"] == day("6-07")
        assert result["project_end"] == day("6-18")
        assert dates_of(result, "B") == ("6-10", "6-11", "6-17", "6-18")
        # A has to finish the working day before B's latest start
        assert dates_of(result, "A") == ("6-07", "6-09", "6-14", "6-16")
        assert floats(result) == {"A": 5, "B": 5, "C": 0}
        assert result["critical_ids"] == ["C"]
        assert result["items"]["C"]["is_critical"] is True
        assert result["items"]["A"]["is_critical"] is False

    def test_a_chain_without_gaps_is_critical_from_end_to_end(self):
        result = analyse(
            [item("A", "6-07", "6-09"), item("B", "6-10", "6-11"), item("C", "6-14", "6-18")],
            [blocked_by("B", "A"), blocked_by("C", "B")],
        )
        assert floats(result) == {"A": 0, "B": 0, "C": 0}
        assert sorted(result["critical_ids"]) == ["A", "B", "C"]

    def test_a_gap_before_the_successor_is_float_of_the_predecessor(self):
        # B could start on 10 June but is planned for 14 June: A may slip by those two working days
        result = analyse([item("A", "6-07", "6-09"), item("B", "6-14", "6-15")], [blocked_by("B", "A")])
        assert floats(result) == {"A": 2, "B": 0}
        assert dates_of(result, "A") == ("6-07", "6-09", "6-09", "6-11")

    def test_lag_asks_for_free_working_days_in_between(self):
        # two free days (9 and 10 June) between A and B: no float left
        tight = analyse([item("A", "6-07", "6-08"), item("B", "6-11", "6-14")], [blocked_by("B", "A", lag=2)])
        assert floats(tight) == {"A": 0, "B": 0}
        # B two working days later: A gets them as float
        loose = analyse([item("A", "6-07", "6-08"), item("B", "6-15", "6-16")], [blocked_by("B", "A", lag=2)])
        assert floats(loose) == {"A": 2, "B": 0}
        assert loose["items"]["A"]["latest_finish"] == day("6-10")

    def test_a_lead_lets_them_share_a_day(self):
        result = analyse([item("A", "6-07", "6-09"), item("B", "6-09", "6-10")], [blocked_by("B", "A", lag=-1)])
        assert floats(result) == {"A": 0, "B": 0}


@pytest.mark.unit
class TestOtherRelationTypes:
    def test_start_to_start(self):
        # B cannot start before A: A's start is as critical as B's although A ends long before the end
        result = analyse(
            [item("A", "6-07", "6-08"), item("B", "6-07", "6-18")],
            [("A", "B", "start_before", 0)],
        )
        assert floats(result) == {"A": 0, "B": 0}
        assert dates_of(result, "A") == ("6-07", "6-08", "6-07", "6-08")

    def test_start_to_start_with_lag(self):
        # B starts at least one working day after A; B has 7 days of float, so A's start has too, but A itself
        # runs to the end and stays critical
        result = analyse(
            [item("A", "6-07", "6-18"), item("B", "6-08", "6-09")],
            [("A", "B", "start_before", 1)],
        )
        assert floats(result) == {"A": 0, "B": 7}
        assert dates_of(result, "B") == ("6-08", "6-09", "6-17", "6-18")

    def test_finish_to_finish(self):
        # B finishes no earlier than A; C sets the end a week later
        result = analyse(
            [item("A", "6-07", "6-18"), item("B", "6-14", "6-18"), item("C", "6-07", "6-25")],
            [("A", "B", "finish_before", 0)],
        )
        assert floats(result) == {"A": 5, "B": 5, "C": 0}
        assert result["items"]["A"]["latest_finish"] == day("6-25")

    def test_finish_to_finish_with_lag(self):
        # B finishes at least 2 working days after A: A has to be done by 23 June for B to end on 25 June
        result = analyse(
            [item("A", "6-07", "6-16"), item("B", "6-14", "6-18"), item("C", "6-07", "6-25")],
            [("A", "B", "finish_before", 2)],
        )
        assert result["items"]["A"]["latest_finish"] == day("6-23")
        assert floats(result) == {"A": 5, "B": 5, "C": 0}

    def test_start_to_finish(self):
        # B cannot finish before 3 working days after A has started (10 June + 3 = 15 June)
        result = analyse(
            [item("A", "6-10", "6-25"), item("B", "6-07", "6-15")],
            [("A", "B", "start_before_finish", 3)],
        )
        # B is free until the end: 16, 17, 18, 21, 22, 23, 24, 25 June
        assert floats(result) == {"A": 0, "B": 8}

    def test_a_predecessor_pushes_the_finish_and_the_start_follows(self):
        # B is planned to finish on 11 June although A only finishes on 16 June: a broken finish-to-finish rule
        result = analyse(
            [item("A", "6-07", "6-16"), item("B", "6-09", "6-11")],
            [("A", "B", "finish_before", 0)],
        )
        # B keeps its 3 working days and ends with A
        assert dates_of(result, "B")[:2] == ("6-14", "6-16")


@pytest.mark.unit
class TestWorkingDays:
    items = [item("A", "6-07", "6-11"), item("B", "6-14", "6-15")]
    relations = [blocked_by("B", "A")]

    def test_a_weekend_between_two_work_items_is_no_float(self):
        assert floats(analyse(self.items, self.relations)) == {"A": 0, "B": 0}

    def test_without_weekend_days_the_same_two_days_are_float(self):
        result = analyse(self.items, self.relations, weekend_days=())
        assert floats(result) == {"A": 2, "B": 0}
        assert result["items"]["A"]["latest_finish"] == day("6-13")

    def test_dates_on_a_weekend_day_count_as_the_nearest_working_day(self):
        # starts on a Saturday, finishes on a Sunday
        result = analyse([item("A", "6-12", "6-20")])
        assert dates_of(result, "A") == ("6-14", "6-18", "6-14", "6-18")
        assert result["project_end"] == day("6-18")

    def test_a_work_item_made_of_a_weekend_only_lasts_one_day(self):
        result = analyse([item("A", "6-12", "6-13")])
        assert dates_of(result, "A")[:2] == ("6-14", "6-14")

    def test_float_counts_working_days_over_several_weeks(self):
        result = analyse([item("A", "6-07", "6-08"), item("B", "6-07", "7-02")])
        # 9-11, 14-18, 21-25 June, 28 June - 2 July
        assert floats(result)["A"] == 18

    def test_a_working_saturday(self):
        # only Sunday is a weekend day: B starts the Saturday after A's Friday finish and nothing is free
        result = analyse(
            [item("A", "6-07", "6-11"), item("B", "6-12", "6-14")], [blocked_by("B", "A")], weekend_days=(0,)
        )
        assert floats(result) == {"A": 0, "B": 0}
        assert result["items"]["B"]["earliest_finish"] == day("6-14")


@pytest.mark.unit
class TestFixedPoints:
    def test_completed_and_cancelled_work_items_have_no_float_and_keep_their_dates(self):
        result = analyse(
            [
                item("done", "6-07", "6-09", group="completed"),
                item("dropped", "6-07", "6-08", group="cancelled"),
                item("open", "6-07", "6-30"),
            ]
        )
        for id in ("done", "dropped"):
            entry = result["items"][id]
            assert entry["is_fixed"] is True
            assert entry["total_float"] is None
            assert entry["is_critical"] is False
            assert (entry["latest_start"], entry["latest_finish"]) == (
                entry["earliest_start"],
                entry["earliest_finish"],
            )
        assert result["critical_ids"] == ["open"]

    def test_a_completed_successor_asks_nothing_of_its_predecessor(self):
        # C is done already, so B is only held by the end of the project
        result = analyse(
            [
                item("B", "6-10", "6-11"),
                item("C", "6-14", "6-15", group="completed"),
                item("D", "6-07", "6-30"),
            ],
            [blocked_by("C", "B")],
        )
        # 14-18, 21-25, 28-30 June
        assert floats(result)["B"] == 13

    def test_a_completed_predecessor_still_holds_its_successor(self):
        # B is planned to start before the completed A ended: its earliest start is the day after A
        result = analyse(
            [item("A", "6-07", "6-11", group="completed"), item("B", "6-10", "6-14")],
            [blocked_by("B", "A")],
        )
        # B keeps its 3 working days
        assert dates_of(result, "B")[:2] == ("6-14", "6-16")
        assert result["project_end"] == day("6-16")

    def test_a_completed_work_item_is_never_moved(self):
        result = analyse(
            [item("A", "6-07", "6-11"), item("B", "6-09", "6-10", group="completed")],
            [blocked_by("B", "A")],
        )
        assert dates_of(result, "B") == ("6-09", "6-10", "6-09", "6-10")
        assert floats(result)["A"] == 0


@pytest.mark.unit
class TestCycles:
    def test_a_cycle_is_reported_and_the_rest_is_analysed(self):
        result = analyse(
            [
                item("A", "6-07", "6-08"),
                item("B", "6-07", "6-08"),
                item("C", "6-09", "6-10"),
                item("D", "6-07", "6-07"),
            ],
            [blocked_by("A", "B"), blocked_by("B", "A"), blocked_by("C", "A")],
        )
        assert [sorted(cycle) for cycle in result["cycles"]] == [["A", "B"]]
        assert set(result["items"]) == {"A", "B", "C", "D"}
        # the relations inside the circle are left out, the one leaving it still counts
        assert dates_of(result, "A")[:2] == ("6-07", "6-08")
        assert floats(result) == {"A": 0, "B": 2, "C": 0, "D": 3}

    def test_a_cycle_across_relation_types(self):
        result = analyse(
            [item("A", "6-07", "6-08"), item("B", "6-07", "6-08")],
            [("A", "B", "start_before", 0), ("B", "A", "finish_before", 0)],
        )
        assert [sorted(cycle) for cycle in result["cycles"]] == [["A", "B"]]

    def test_a_relation_of_a_work_item_with_itself_is_ignored(self):
        result = analyse([item("A", "6-07", "6-08")], [blocked_by("A", "A")])
        assert result["cycles"] == []
        assert floats(result) == {"A": 0}

    def test_a_long_chain_does_not_hit_the_recursion_limit(self):
        count = 3000
        items = [item(index, "6-07", "6-07") for index in range(count)]
        relations = [blocked_by(index + 1, index) for index in range(count - 1)]
        result = analyse(items, relations, weekend_days=())
        assert result["cycles"] == []
        # every work item is planned on the same day, so the chain pushes each one a day later
        assert result["items"][count - 1]["earliest_start"].toordinal() - day("6-07").toordinal() == count - 1
        assert len(result["critical_ids"]) == count


@pytest.mark.unit
class TestUndated:
    def test_work_items_without_both_dates_are_left_out_and_counted(self):
        result = analyse(
            [
                item("A", "6-07", "6-08"),
                item("start only", "6-09"),
                item("finish only", None, "6-10"),
                item("none"),
            ],
            [blocked_by("start only", "A"), blocked_by("A", "none")],
        )
        assert set(result["items"]) == {"A"}
        assert result["undated_count"] == 3
        # only the ones a relation meets are listed: the chain is broken there
        assert result["undated_linked_ids"] == ["none", "start only"]
        assert floats(result) == {"A": 0}

    def test_relations_to_work_items_that_are_not_given_are_ignored(self):
        result = analyse([item("A", "6-07", "6-08")], [blocked_by("A", "elsewhere"), blocked_by("elsewhere", "A")])
        assert floats(result) == {"A": 0}
        assert result["undated_linked_ids"] == []

    def test_relation_types_without_dates_are_ignored(self):
        result = analyse(
            [item("A", "6-07", "6-08"), item("B", "6-07", "6-11")],
            [("A", "B", "relates_to", 0), ("A", "B", "duplicate", 0), ("A", "B", "implemented_by", 0)],
        )
        assert floats(result) == {"A": 3, "B": 0}

    def test_nothing_to_analyse(self):
        result = analyse([])
        assert result["project_start"] is None and result["project_end"] is None
        assert result["items"] == {} and result["critical_ids"] == [] and result["cycles"] == []


@pytest.mark.unit
class TestNeededBy:
    def test_a_due_date_downstream_gives_the_date_a_work_item_is_needed_by(self):
        # C is due on 18 June and lasts 2 days: it has to start on 17 June, so B is needed by 16 June;
        # B lasts 3 days and has to start on 14 June, so A is needed by 11 June
        result = analyse(
            [item("A", "6-07", "6-08"), item("B", "6-09", "6-11"), item("C", "6-14", "6-15", due="6-18")],
            [blocked_by("B", "A"), blocked_by("C", "B")],
        )
        needed = {id: entry["needed_by"] for id, entry in result["items"].items()}
        assert needed == {"A": day("6-11"), "B": day("6-16"), "C": None}
        # due dates do not change float: the chain is critical because it sets the end
        assert floats(result) == {"A": 0, "B": 0, "C": 0}

    def test_no_due_date_downstream_means_no_needed_by(self):
        result = analyse([item("A", "6-07", "6-08", due="6-08"), item("B", "6-09", "6-11")], [blocked_by("B", "A")])
        assert result["items"]["A"]["needed_by"] is None
        assert result["items"]["B"]["needed_by"] is None

    def test_the_tightest_due_date_wins(self):
        result = analyse(
            [
                item("A", "6-07", "6-08"),
                item("B", "6-09", "6-09", due="6-25"),
                item("C", "6-09", "6-10", due="6-15"),
            ],
            [blocked_by("B", "A"), blocked_by("C", "A")],
        )
        # C has to start on 14 June at the latest
        assert result["items"]["A"]["needed_by"] == day("6-11")

    def test_a_needed_by_date_may_already_be_missed(self):
        result = analyse(
            [item("A", "6-07", "6-11"), item("B", "6-14", "6-16", due="6-15")],
            [blocked_by("B", "A")],
        )
        # B (3 days) has to start on 11 June to be done on 15 June
        assert result["items"]["A"]["needed_by"] == day("6-10")

    def test_a_due_date_of_a_completed_work_item_no_longer_matters(self):
        result = analyse(
            [item("A", "6-07", "6-08"), item("B", "6-09", "6-11", due="6-11", group="completed")],
            [blocked_by("B", "A")],
        )
        assert result["items"]["A"]["needed_by"] is None


def closure_samples_network():
    """A network in the style of module 5a ("samples of new closures: waiting for the supplier") of the Gantt-RACI
    demo dataset, with the neighbours that give it float. Lengths are in working days.

    e1 choose bottle and closure        7-11 June (5)
    c1 ask for samples                  14 June (1)            after e1
    c2 wait for the supplier            15-28 June (10)        after c1
    c3 order samples                    29 June - 1 July (3)   after c2
    c4 send samples to the line         2-5 July (2)           after c3, due 6 July
    e2 label design                     14-25 June (10)        after e1
    e3 mandatory label content          21-25 June (5)         finishes no earlier than e2
    s2 pallet scheme                    14-18 June (5)         after e1
    z1 collective packaging design      28 June - 9 July (10)  after e2 and s2
    d3 ERP records                      9-15 June (5)          starts 2 working days after e1 at the earliest
    """
    items = [
        item("e1", "6-07", "6-11"),
        item("c1", "6-14", "6-14"),
        item("c2", "6-15", "6-28"),
        item("c3", "6-29", "7-01"),
        item("c4", "7-02", "7-05", due="7-06"),
        item("e2", "6-14", "6-25"),
        item("e3", "6-21", "6-25"),
        item("s2", "6-14", "6-18"),
        item("z1", "6-28", "7-09"),
        item("d3", "6-09", "6-15"),
    ]
    relations = [
        blocked_by("c1", "e1"),
        blocked_by("c2", "c1"),
        blocked_by("c3", "c2"),
        blocked_by("c4", "c3"),
        blocked_by("e2", "e1"),
        ("e2", "e3", "finish_before", 0),
        blocked_by("s2", "e1"),
        blocked_by("z1", "e2"),
        blocked_by("z1", "s2"),
        ("e1", "d3", "start_before", 2),
    ]
    return items, relations


@pytest.mark.unit
class TestClosureSamplesNetwork:
    @pytest.fixture
    def result(self):
        return analyse(*closure_samples_network())

    def test_the_plan_keeps_every_relation_so_the_earliest_dates_are_the_planned_ones(self, result):
        items, _ = closure_samples_network()
        for entry in items:
            analysed = result["items"][entry["id"]]
            assert (analysed["earliest_start"], analysed["earliest_finish"]) == (
                entry["start_date"],
                entry["finish_date"],
            )
        assert (result["project_start"], result["project_end"]) == (day("6-07"), day("7-09"))

    def test_the_critical_path_runs_through_the_label_and_the_collective_packaging(self, result):
        assert sorted(result["critical_ids"]) == ["e1", "e2", "z1"]

    def test_float(self, result):
        assert floats(result) == {
            "e1": 0,
            "e2": 0,
            "z1": 0,
            # the supplier chain ends on 5 July, four working days before the end, and shares that float
            "c1": 4,
            "c2": 4,
            "c3": 4,
            "c4": 4,
            # z1 starts on 28 June, a week after the pallet scheme is done
            "s2": 5,
            "e3": 10,
            "d3": 18,
        }

    def test_latest_dates(self, result):
        assert dates_of(result, "c2")[2:] == ("6-21", "7-02")
        assert dates_of(result, "c4")[2:] == ("7-08", "7-09")
        assert dates_of(result, "s2")[2:] == ("6-21", "6-25")
        assert dates_of(result, "e1")[2:] == ("6-07", "6-11")
        assert dates_of(result, "d3")[2:] == ("7-05", "7-09")

    def test_needed_by_follows_the_due_date_of_the_last_step_back_through_the_supplier_chain(self, result):
        needed = {id: entry["needed_by"] for id, entry in result["items"].items() if entry["needed_by"]}
        assert needed == {
            "c3": day("7-02"),
            "c2": day("6-29"),
            "c1": day("6-15"),
            "e1": day("6-14"),
        }

    def test_a_late_supplier_makes_the_supplier_chain_critical(self):
        items, relations = closure_samples_network()
        # the answer takes 5 working days longer: c2 ends on 5 July, c3 and c4 are replanned after it
        replanned = {"c2": ("6-15", "7-05"), "c3": ("7-06", "7-08"), "c4": ("7-09", "7-12")}
        items = [item(entry["id"], *replanned[entry["id"]]) if entry["id"] in replanned else entry for entry in items]
        result = analyse(items, relations)
        assert result["project_end"] == day("7-12")
        assert sorted(result["critical_ids"]) == ["c1", "c2", "c3", "c4", "e1"]
        assert floats(result)["z1"] == 1


@pytest.mark.unit
class TestSerialize:
    def test_dates_and_ids_become_strings(self):
        payload = serialize_analysis(
            analyse([item("A", "6-07", "6-08"), item("B", "6-09", "6-11", due="6-18")], [blocked_by("B", "A")])
        )
        assert payload["project_end"] == "2027-06-11"
        assert payload["items"]["A"] == {
            "earliest_start": "2027-06-07",
            "earliest_finish": "2027-06-08",
            "latest_start": "2027-06-07",
            "latest_finish": "2027-06-08",
            "total_float": 0,
            "is_critical": True,
            "is_fixed": False,
            "needed_by": "2027-06-15",
        }
        assert sorted(payload["critical_ids"]) == ["A", "B"]
