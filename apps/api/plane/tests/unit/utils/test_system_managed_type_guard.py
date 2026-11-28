# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Unit tests for `refuse_system_managed_type`, the shared guard of the system-managed work item types."""

from types import SimpleNamespace

import pytest

from plane.db.models import IssueTypeKind
from plane.utils.project_issue_types import (
    SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS,
    SYSTEM_MANAGED_TYPE_CODE,
    SYSTEM_MANAGED_TYPE_DEACTIVATE,
    SYSTEM_MANAGED_TYPE_DELETE,
    SYSTEM_MANAGED_TYPE_LINK,
    SYSTEM_MANAGED_TYPE_MAKE_DEFAULT,
    SYSTEM_MANAGED_TYPE_UNLINK,
    IssueTypeChangeRejected,
    refuse_system_managed_type,
)

ACTIONS = [
    SYSTEM_MANAGED_TYPE_DELETE,
    SYSTEM_MANAGED_TYPE_DEACTIVATE,
    SYSTEM_MANAGED_TYPE_LINK,
    SYSTEM_MANAGED_TYPE_UNLINK,
    SYSTEM_MANAGED_TYPE_CHANGE_PROJECTS,
    SYSTEM_MANAGED_TYPE_MAKE_DEFAULT,
]


@pytest.mark.unit
@pytest.mark.parametrize("kind", [IssueTypeKind.APPROVAL, IssueTypeKind.REVIEW])
@pytest.mark.parametrize("action", ACTIONS)
def test_a_system_managed_type_is_refused_with_the_code(kind, action):
    with pytest.raises(IssueTypeChangeRejected) as raised:
        refuse_system_managed_type(SimpleNamespace(kind=kind), action)
    assert raised.value.status_code == 400
    assert raised.value.detail["error_code"] == SYSTEM_MANAGED_TYPE_CODE
    assert raised.value.detail["error"]


@pytest.mark.unit
@pytest.mark.parametrize("kind", [IssueTypeKind.STANDARD, IssueTypeKind.EPIC, IssueTypeKind.MILESTONE])
@pytest.mark.parametrize("action", ACTIONS)
def test_other_kinds_pass(kind, action):
    refuse_system_managed_type(SimpleNamespace(kind=kind), action)


@pytest.mark.unit
def test_no_type_passes():
    refuse_system_managed_type(None, SYSTEM_MANAGED_TYPE_DELETE)
