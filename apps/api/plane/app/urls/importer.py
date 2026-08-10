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
