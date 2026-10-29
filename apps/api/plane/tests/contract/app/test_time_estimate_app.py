# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import Estimate, EstimatePoint, Project, ProjectMember
from plane.db.models.estimate import EstimateType


@pytest.mark.unit
def test_time_is_an_estimate_type():
    assert EstimateType.TIME == "time"
    assert ("time", "Time") in EstimateType.choices


@pytest.mark.contract
@pytest.mark.django_db
def test_a_time_estimate_system_can_be_created(session_client, workspace, create_user):
    project = Project.objects.create(name="Estimates", identifier="EST", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20)

    response = session_client.post(
        f"/api/workspaces/{workspace.slug}/projects/{project.id}/estimates/",
        {
            "estimate": {"name": "Time", "type": "time", "last_used": True},
            "estimate_points": [{"key": 1, "value": "60"}, {"key": 2, "value": "90"}, {"key": 3, "value": "120"}],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["type"] == "time"
    assert sorted((point["value"] for point in response.data["points"]), key=int) == ["60", "90", "120"]
    estimate = Estimate.objects.get(project=project)
    assert estimate.type == "time"
    assert list(EstimatePoint.objects.filter(estimate=estimate).order_by("key").values_list("value", flat=True)) == [
        "60",
        "90",
        "120",
    ]
