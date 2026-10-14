# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date
from types import SimpleNamespace

import pytest
from plane.utils.work_item_dates import (
    FINISH_BEFORE_START_MESSAGE,
    INITIALIZE_PAIRED_DATE_KEY,
    PAIRED_DATE_DEFAULTED_KEY,
    WorkItemDateError,
    date_statuses,
    resolve_for_logging,
    resolve_work_item_dates,
)

TODAY = date(2026, 10, 10)  # frozen project-local today for the status tests


def work_item(start=None, finish=None, due=None, initialized=False, duration=None):
    return SimpleNamespace(
        start_date=start,
        finish_date=finish,
        target_date=due,
        dates_initialized=initialized,
        duration=duration,
    )


def init(**payload):
    return {INITIALIZE_PAIRED_DATE_KEY: True, **payload}


@pytest.mark.unit
class TestInitialEqualityRule:
    def test_fresh_item_has_no_dates_and_nothing_is_derived(self):
        assert resolve_work_item_dates(work_item(), {"name": "x"}).fields == {}

    def test_first_finish_with_initialization_sets_due_too(self):
        result = resolve_work_item_dates(work_item(), init(finish_date="2026-10-20"))
        assert result.fields["target_date"] == "2026-10-20"
        assert result.fields["target_date_origin"] == "defaulted"
        assert result.fields["finish_date_origin"] == "manual"
        assert result.fields["dates_initialized"] is True
        assert "start_date" not in result.fields
        assert result.notices == [{"code": "due_date_defaulted", "date": "2026-10-20"}]

    def test_first_due_with_initialization_sets_finish_too(self):
        result = resolve_work_item_dates(work_item(), init(target_date="2026-10-23"))
        assert result.fields["finish_date"] == "2026-10-23"
        assert result.fields["finish_date_origin"] == "defaulted"
        assert result.fields["target_date_origin"] == "manual"
        assert "start_date" not in result.fields

    def test_creation_without_an_instance_works(self):
        result = resolve_work_item_dates(None, init(finish_date="2026-10-20"))
        assert result.fields["target_date"] == "2026-10-20"

    def test_opt_out_sets_only_the_supplied_date(self):
        result = resolve_work_item_dates(work_item(), {"finish_date": "2026-10-20"})
        assert "target_date" not in result.fields
        assert result.fields["dates_initialized"] is True  # still consumed
        assert result.notices == []

    def test_start_only_edit_does_not_consume_the_opportunity(self):
        result = resolve_work_item_dates(work_item(), init(start_date="2026-10-19"))
        assert "dates_initialized" not in result.fields

    def test_start_only_then_first_valid_finish_initializes_both(self):
        item = work_item(start=date(2026, 10, 19))
        result = resolve_work_item_dates(item, init(finish_date="2026-10-21"))
        assert result.fields["target_date"] == "2026-10-21"
        assert result.fields["duration"] == 3

    def test_first_due_before_start_keeps_finish_empty_and_explains(self):
        item = work_item(start=date(2026, 10, 19))
        result = resolve_work_item_dates(item, init(target_date="2026-10-12"))
        assert "finish_date" not in result.fields
        assert result.notices == [{"code": "finish_date_not_defaulted", "date": "2026-10-12"}]
        assert result.fields["dates_initialized"] is True

    def test_equal_dates_are_not_linked(self):
        item = work_item(finish=date(2026, 10, 20), due=date(2026, 10, 20), initialized=True)
        assert "target_date" not in resolve_work_item_dates(item, init(finish_date="2026-10-22")).fields
        assert "finish_date" not in resolve_work_item_dates(item, init(target_date="2026-10-23")).fields

    def test_existing_value_is_never_overwritten_even_if_not_yet_consumed(self):
        item = work_item(due=date(2026, 10, 1))
        result = resolve_work_item_dates(item, init(finish_date="2026-10-20"))
        assert "target_date" not in result.fields

    def test_deliberately_cleared_field_is_not_refilled(self):
        item = work_item(finish=date(2026, 10, 20), initialized=True)
        result = resolve_work_item_dates(item, init(finish_date="2026-10-22"))
        assert "target_date" not in result.fields

    def test_clearing_both_then_entering_one_does_not_restart_copying(self):
        cleared = resolve_work_item_dates(
            work_item(finish=date(2026, 10, 20), due=date(2026, 10, 20)),
            {"finish_date": None, "target_date": None},
        )
        assert cleared.fields["dates_initialized"] is True
        item = work_item(initialized=True)
        assert "finish_date" not in resolve_work_item_dates(item, init(target_date="2026-10-23")).fields

    def test_explicit_finish_with_null_due_is_preserved(self):
        result = resolve_work_item_dates(work_item(), init(finish_date="2026-10-20", target_date=None))
        assert "target_date" not in result.fields or result.fields["target_date"] is None
        assert result.notices == []

    def test_both_supplied_bypasses_copying(self):
        result = resolve_work_item_dates(work_item(), init(finish_date="2026-10-20", target_date="2026-10-30"))
        assert "target_date" not in result.fields or result.fields["target_date"] == "2026-10-30"
        assert result.notices == []

    def test_api_due_only_update_without_intent_leaves_finish_alone(self):
        result = resolve_work_item_dates(work_item(), {"target_date": "2026-10-23"})
        assert "finish_date" not in result.fields
        assert result.notices == []

    def test_import_style_create_never_defaults(self):
        result = resolve_work_item_dates(None, {"target_date": "2026-10-23", "finish_date": None})
        assert result.fields.get("finish_date") is None


@pytest.mark.unit
class TestFormPreviewProvenance:
    def test_creation_form_that_already_shows_both_values_records_the_copied_one(self):
        payload = {"finish_date": "2026-10-20", "target_date": "2026-10-20", PAIRED_DATE_DEFAULTED_KEY: "target_date"}
        result = resolve_work_item_dates(None, payload)
        assert result.fields["target_date_origin"] == "defaulted"
        assert result.fields["finish_date_origin"] == "manual"
        assert result.notices == [{"code": "due_date_defaulted", "date": "2026-10-20"}]

    def test_provenance_claim_is_rejected_when_not_eligible_or_values_differ(self):
        payload = {"finish_date": "2026-10-20", "target_date": "2026-10-21", PAIRED_DATE_DEFAULTED_KEY: "target_date"}
        assert resolve_work_item_dates(None, payload).fields["target_date_origin"] == "manual"
        consumed = work_item(initialized=True)
        equal = {"finish_date": "2026-10-20", "target_date": "2026-10-20", PAIRED_DATE_DEFAULTED_KEY: "target_date"}
        assert resolve_work_item_dates(consumed, equal).fields["target_date_origin"] == "manual"


@pytest.mark.unit
class TestScheduleValidation:
    def test_finish_before_start_is_rejected(self):
        with pytest.raises(WorkItemDateError) as exc:
            resolve_work_item_dates(work_item(start=date(2026, 10, 19)), {"finish_date": "2026-10-18"})
        assert str(exc.value) == FINISH_BEFORE_START_MESSAGE

    def test_start_after_existing_finish_is_rejected(self):
        with pytest.raises(WorkItemDateError):
            resolve_work_item_dates(work_item(finish=date(2026, 10, 20)), {"start_date": "2026-10-25"})

    def test_same_start_and_finish_is_a_one_day_task(self):
        result = resolve_work_item_dates(work_item(), {"start_date": "2026-10-20", "finish_date": "2026-10-20"})
        assert result.fields["duration"] == 1

    def test_finish_after_due_and_due_before_start_are_allowed(self):
        assert resolve_work_item_dates(work_item(due=date(2026, 10, 20)), {"finish_date": "2026-10-22"})
        item = work_item(start=date(2026, 10, 19), finish=date(2026, 10, 20))
        result = resolve_work_item_dates(item, {"target_date": "2026-10-12"})
        assert result.fields.get("finish_date") is None and "start_date" not in result.fields

    def test_direct_finish_edit_leaves_start_and_due_alone(self):
        item = work_item(start=date(2026, 10, 21), finish=date(2026, 10, 23), due=date(2026, 10, 30), initialized=True)
        fields = resolve_work_item_dates(item, {"finish_date": "2026-10-24"}).fields
        assert "start_date" not in fields and "target_date" not in fields
        assert fields["duration"] == 4

    def test_logging_helper_swallows_invalid_schedules(self):
        assert resolve_for_logging(work_item(start=date(2026, 10, 19)), {"finish_date": "2026-10-18"}) == {}


@pytest.mark.unit
class TestDateStatuses:
    def statuses(self, **kw):
        base = dict(finish_date=None, due_date=None, today=TODAY, is_active=True)
        return date_statuses(**{**base, **kw})

    def test_fresh_item_has_no_warnings(self):
        assert not any(self.statuses().values())

    def test_incomplete_item_past_due_is_overdue(self):
        assert self.statuses(due_date=date(2026, 10, 8))["overdue"]

    def test_due_today_is_not_overdue(self):
        assert not self.statuses(due_date=date(2026, 10, 10))["overdue"]

    def test_planned_finish_passed_is_not_overdue(self):
        s = self.statuses(finish_date=date(2026, 10, 8), due_date=date(2026, 10, 20))
        assert s["planned_finish_passed"] and not s["overdue"]

    def test_forecast_misses_deadline_before_the_deadline_passes(self):
        s = self.statuses(finish_date=date(2026, 10, 22), due_date=date(2026, 10, 20))
        assert s["forecast_misses_deadline"] and not s["overdue"]

    def test_due_without_finish_is_forecast_unknown(self):
        assert self.statuses(due_date=date(2026, 10, 20))["forecast_unknown"]

    def test_completed_item_loses_active_warnings(self):
        s = self.statuses(due_date=date(2026, 10, 8), is_active=False)
        assert not s["overdue"] and not s["forecast_unknown"]

    def test_completed_late_uses_the_due_date_at_completion(self):
        s = self.statuses(
            is_active=False,
            due_date=date(2026, 12, 1),  # deadline was extended later
            completed_on=date(2026, 10, 9),
            due_at_completion=date(2026, 10, 8),
        )
        assert s["completed_late"]
        s = self.statuses(is_active=False, completed_on=date(2026, 10, 8), due_at_completion=date(2026, 10, 8))
        assert not s["completed_late"]
