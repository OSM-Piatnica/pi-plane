# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import Project, ProjectMember


@pytest.mark.contract
class TestProjectListCreateAPIEndpoint:
    """Contract tests for GET /api/v1/workspaces/{slug}/projects/ order_by handling."""

    def get_url(self, workspace_slug):
        return f"/api/v1/workspaces/{workspace_slug}/projects/"

    @pytest.mark.django_db
    def test_list_invalid_order_by_does_not_500(self, api_key_client, workspace, create_user):
        """Regression for GHSA-p885-6jpg-cr2p (DoS half).

        An unknown ``order_by`` field used to reach Django's ``.order_by()``
        raw and raise a ``FieldError`` -> HTTP 500. After the fix the value is
        sanitized to the safe default and the endpoint returns 200.
        """
        project = Project.objects.create(
            name="Ordered Project",
            identifier="OP",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        response = api_key_client.get(self.get_url(workspace.slug), {"order_by": "not_a_field"})

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"

    @pytest.mark.django_db
    def test_list_relational_order_by_injection_does_not_500(self, api_key_client, workspace, create_user):
        """Regression for GHSA-p885-6jpg-cr2p (relational-traversal leak half).

        Ordering by a related-table column (``created_by__password``) used to
        reach ``.order_by()`` raw, forming a blind ordering oracle. After the
        fix the value is not in ``PROJECT_ORDER_BY_ALLOWLIST`` and is replaced
        with the safe default, so it can no longer influence SQL ordering.
        (That the payload maps to the default is asserted deterministically in
        tests/unit/utils/test_order_by_sanitize.py.)
        """
        project = Project.objects.create(
            name="Oracle Project",
            identifier="OR",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)

        response = api_key_client.get(self.get_url(workspace.slug), {"order_by": "created_by__password"})

        assert response.status_code == status.HTTP_200_OK, f"Got {response.status_code}: {response.data!r}"
