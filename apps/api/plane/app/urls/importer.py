from django.urls import path

from plane.app.views import ImportProjectsEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/import-projects/",
        ImportProjectsEndpoint.as_view(),
        name="import-projects",
    ),
]
