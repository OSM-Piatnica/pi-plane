import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import ProjectTemplate


@pytest.mark.contract
class TestProjectTemplateUpdateAPI:
    @pytest.mark.django_db
    def test_create_and_patch_project_template(self, session_client, workspace):
        list_url = reverse("workspace-project-templates", kwargs={"slug": workspace.slug})
        create_response = session_client.post(
            list_url,
            {
                "name": "Software delivery",
                "description": "Starter setup",
                "payload": {
                    "name": "New product",
                    "identifier": "PROD",
                    "cycle_view": True,
                    "module_view": False,
                },
            },
            format="json",
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        template_id = create_response.data["id"]

        detail_url = reverse(
            "workspace-project-templates-detail",
            kwargs={"slug": workspace.slug, "pk": template_id},
        )
        patch_response = session_client.patch(
            detail_url,
            {
                "name": "Updated delivery template",
                "payload": {
                    "name": "Renamed product",
                    "identifier": "REN",
                    "module_view": True,
                },
            },
            format="json",
        )

        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.data["name"] == "Updated delivery template"
        assert patch_response.data["payload"]["name"] == "Renamed product"
        assert patch_response.data["payload"]["identifier"] == "REN"
        assert patch_response.data["payload"]["module_view"] is True

        template = ProjectTemplate.objects.get(id=template_id)
        assert template.name == "Updated delivery template"
