# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from uuid import uuid4

import pytest

from plane.bgtasks.issue_activities_task import (
    _format_worklog_duration,
    create_worklog_activity,
    delete_worklog_activity,
    update_worklog_activity,
)


def call(function, requested, current=None):
    activities = []
    function(
        requested_data=json.dumps(requested),
        current_instance=json.dumps(current) if current is not None else None,
        issue_id=uuid4(),
        project_id=uuid4(),
        workspace_id=uuid4(),
        actor_id=uuid4(),
        issue_activities=activities,
        epoch=1,
    )
    assert len(activities) == 1
    return activities[0]


@pytest.mark.unit
class TestWorklogActivities:
    @pytest.mark.parametrize(
        "minutes,text", [(1, "1m"), (59, "59m"), (60, "1h"), (150, "2h 30m"), (1440, "24h"), (0, "0m"), (None, "0m")]
    )
    def test_duration_text(self, minutes, text):
        assert _format_worklog_duration(minutes) == text

    def test_created(self):
        activity = call(create_worklog_activity, {"duration": 150})
        assert (activity.field, activity.verb, activity.new_value, activity.old_value) == (
            "worklog",
            "created",
            "2h 30m",
            None,
        )

    def test_updated_keeps_the_old_and_the_new_duration(self):
        activity = call(update_worklog_activity, {"duration": 45}, {"duration": 150})
        assert (activity.field, activity.verb, activity.old_value, activity.new_value) == (
            "worklog",
            "updated",
            "2h 30m",
            "45m",
        )

    def test_deleted_keeps_the_removed_duration(self):
        activity = call(delete_worklog_activity, {"duration": 60})
        assert (activity.field, activity.verb, activity.old_value) == ("worklog", "deleted", "1h")
