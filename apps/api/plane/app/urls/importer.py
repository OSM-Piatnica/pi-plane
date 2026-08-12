# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from django.urls import path

from plane.app.views import ImportProjectsEndpoint, ImportWorkItemsEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/import-projects/",
        ImportProjectsEndpoint.as_view(),
        name="import-projects",
    ),
    path(
        "workspaces/<str:slug>/import-work-items/",
        ImportWorkItemsEndpoint.as_view(),
        name="import-work-items",
    ),
]
