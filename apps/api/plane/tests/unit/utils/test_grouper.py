# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

import pytest

from plane.db.models import Issue
from plane.utils.grouper import issue_group_values, issue_queryset_grouper


@pytest.mark.unit
def test_issue_group_values_requires_project_or_user():
    with pytest.raises(ValueError):
        issue_group_values(field="state_id", slug="workspace")


@pytest.mark.unit
@pytest.mark.parametrize("group_by", [None, "state_id", "assignees__id"])
def test_never_grouped_annotations_are_added_to_every_list(group_by):
    """``raci`` and ``group_assignee_ids`` are never a grouping, so every list gets them, an ungrouped one too
    (``group_by`` None, as the answer to a work item create reads it: without it that answer failed with a
    FieldError)."""
    annotations = issue_queryset_grouper(Issue.objects.all(), group_by=group_by, sub_group_by=None).query.annotations

    assert {"raci", "group_assignee_ids"} <= set(annotations)
