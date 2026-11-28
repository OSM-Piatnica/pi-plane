# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The deadline warning of the shift offer: how far a shifted work item passes its due date, in working days.

2 November 2026 is a Monday; Saturday and Sunday are the weekend unless a test says otherwise.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from plane.utils.issue_reschedule import ReschedulePlan, deadline_overrun, deadline_warning

WEEKEND = (0, 6)
MON, TUE, WED, THU, FRI, SAT, SUN = (date(2026, 11, day) for day in range(2, 9))
NEXT_MON, NEXT_TUE = date(2026, 11, 9), date(2026, 11, 10)


def issue(finish=None, due=None, start=None, weekend_days=WEEKEND):
    project = SimpleNamespace(identifier="DEMO", weekend_days=list(weekend_days))
    return SimpleNamespace(
        id="i41",
        project_id="p1",
        project=project,
        sequence_id=41,
        name="Print run",
        start_date=start,
        finish_date=finish,
        target_date=due,
    )


@pytest.mark.unit
class TestDeadlineOverrun:
    def test_finishing_on_or_before_the_due_date_is_not_late(self):
        assert deadline_overrun(WED, WED, WEEKEND) == 0
        assert deadline_overrun(TUE, WED, WEEKEND) == 0

    def test_counts_working_days_after_the_due_date(self):
        assert deadline_overrun(FRI, WED, WEEKEND) == 2
        # Thursday, Friday and Monday: the weekend does not count
        assert deadline_overrun(NEXT_MON, WED, WEEKEND) == 3

    def test_a_finish_on_the_weekend_after_a_friday_due_date_is_not_late(self):
        assert deadline_overrun(SAT, FRI, WEEKEND) == 0
        assert deadline_overrun(SUN, FRI, WEEKEND) == 0
        assert deadline_overrun(NEXT_MON, FRI, WEEKEND) == 1

    def test_a_due_date_on_the_weekend_is_met_by_the_friday_before(self):
        assert deadline_overrun(FRI, SAT, WEEKEND) == 0
        assert deadline_overrun(NEXT_MON, SAT, WEEKEND) == 1

    def test_without_a_weekend_every_day_counts(self):
        assert deadline_overrun(NEXT_MON, FRI, ()) == 3

    def test_a_missing_date_is_never_late(self):
        assert deadline_overrun(None, WED, WEEKEND) == 0
        assert deadline_overrun(FRI, None, WEEKEND) == 0

    def test_takes_iso_strings(self):
        assert deadline_overrun("2026-11-09", "2026-11-04", WEEKEND) == 3


@pytest.mark.unit
class TestDeadlineWarning:
    def test_a_shift_past_the_due_date_is_warned_about(self):
        assert deadline_warning(issue(finish=WED, due=WED), NEXT_MON) == {
            "deadline_overrun_days": 3,
            "previous_deadline_overrun_days": None,
        }

    def test_a_shift_that_stays_within_the_due_date_is_not(self):
        assert deadline_warning(issue(finish=MON, due=FRI), THU) == {
            "deadline_overrun_days": None,
            "previous_deadline_overrun_days": None,
        }

    def test_no_due_date_no_warning(self):
        assert deadline_warning(issue(finish=MON), NEXT_TUE)["deadline_overrun_days"] is None

    def test_an_item_late_already_is_warned_about_with_the_overrun_it_had(self):
        assert deadline_warning(issue(finish=WED, due=TUE), NEXT_MON) == {
            "deadline_overrun_days": 4,
            "previous_deadline_overrun_days": 1,
        }

    def test_an_item_late_already_that_gets_no_later_is_not_warned_about(self):
        # Friday to Sunday: still one working day past the Thursday due date
        assert deadline_warning(issue(finish=FRI, due=THU), SUN)["deadline_overrun_days"] is None

    def test_counts_with_the_weekend_of_the_items_own_project(self):
        assert deadline_warning(issue(finish=WED, due=WED, weekend_days=()), NEXT_MON)["deadline_overrun_days"] == 5


@pytest.mark.unit
def test_the_offer_lists_the_due_date_and_the_warning_per_shifted_item():
    late = issue(start=MON, finish=WED, due=WED)
    plan = ReschedulePlan(shifted={"i41": {"issue": late, "start_date": THU, "finish_date": NEXT_MON, "cause_id": "x"}})

    (shift,) = plan.payload({"error_code": "relation_date_conflict"})["shifts"]

    assert shift["ref"] == "DEMO-41"
    assert shift["target_date"] == "2026-11-04"
    assert shift["new_finish_date"] == "2026-11-09"
    assert shift["deadline_overrun_days"] == 3
    assert shift["previous_deadline_overrun_days"] is None
