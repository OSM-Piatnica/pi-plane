# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.api.views import ProjectGroupDetailAPIEndpoint, ProjectGroupListCreateAPIEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/groups/",
        ProjectGroupListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="project-groups",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/groups/<uuid:pk>/",
        ProjectGroupDetailAPIEndpoint.as_view(http_method_names=["patch", "delete"]),
        name="project-group",
    ),
]
