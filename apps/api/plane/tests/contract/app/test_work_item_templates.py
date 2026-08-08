import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import Project, ProjectMember, WorkItemTemplate


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Template Test Project",
        identifier="TTP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )
    return project


@pytest.mark.contract
class TestWorkItemTemplateUpdateAPI:
    @pytest.mark.django_db
    def test_create_and_patch_work_item_template(self, session_client, workspace):
        list_url = reverse("workspace-work-item-templates", kwargs={"slug": workspace.slug})
        create_response = session_client.post(
            list_url,
            {
                "name": "Bug template",
                "description": "Team note",
                "payload": {
                    "name": "Bug report",
                    "description_html": "<p>Steps to reproduce</p>",
                    "priority": "high",
                },
            },
            format="json",
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        template_id = create_response.data["id"]

        detail_url = reverse(
            "workspace-work-item-templates-detail",
            kwargs={"slug": workspace.slug, "pk": template_id},
        )
        patch_response = session_client.patch(
            detail_url,
            {
                "name": "Updated bug template",
                "description": "Updated note",
                "payload": {
                    "name": "Updated bug",
                    "description_html": "<p>Updated steps</p>",
                    "priority": "low",
                },
            },
            format="json",
        )

        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.data["name"] == "Updated bug template"
        assert patch_response.data["description"] == "Updated note"
        assert patch_response.data["payload"]["name"] == "Updated bug"
        assert patch_response.data["payload"]["priority"] == "low"

        template = WorkItemTemplate.objects.get(id=template_id)
        assert template.name == "Updated bug template"
