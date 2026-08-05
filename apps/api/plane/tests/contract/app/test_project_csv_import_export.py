import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from plane.db.models import Label, Project, ProjectMember, State
from plane.utils.porters.formatters import CSVFormatter


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Export Source",
        identifier="EXP",
        workspace=workspace,
        created_by=create_user,
        description="Source project",
        cycle_view=True,
    )
    ProjectMember.objects.create(
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )
    State.objects.create(
        name="Review",
        color="#123456",
        project=project,
        workspace=workspace,
        group="started",
        sequence=50000,
        created_by=create_user,
    )
    Label.objects.create(
        name="Bug",
        color="#654321",
        project=project,
        workspace=workspace,
        sort_order=10000,
        created_by=create_user,
    )
    return project


@pytest.mark.contract
class TestProjectCsvImportAPI:
    @pytest.mark.django_db
    def test_import_project_from_csv(self, session_client, workspace):
        csv_content = CSVFormatter().encode(
            [
                {
                    "name": "Imported Project",
                    "identifier": "IMP",
                    "description": "From CSV",
                    "state_templates": [{"name": "QA", "group": "started", "color": "#112233"}],
                    "label_templates": [{"name": "Feature", "color": "#445566"}],
                }
            ]
        )
        url = reverse("import-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "file": SimpleUploadedFile("project.csv", csv_content.encode("utf-8"), content_type="text/csv"),
                "provider": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(identifier="IMP", workspace=workspace)
        assert project.name == "Imported Project"
        assert State.objects.filter(project=project, name="QA").exists()
        assert Label.objects.filter(project=project, name="Feature").exists()

    @pytest.mark.django_db
    def test_import_rejects_duplicate_identifier(self, session_client, workspace, project):
        csv_content = CSVFormatter().encode(
            [{"name": "Duplicate", "identifier": project.identifier, "description": ""}]
        )
        url = reverse("import-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "file": SimpleUploadedFile("project.csv", csv_content.encode("utf-8"), content_type="text/csv"),
                "provider": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_import_rejects_empty_csv(self, session_client, workspace):
        url = reverse("import-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "file": SimpleUploadedFile("empty.csv", b"name,identifier\n", content_type="text/csv"),
                "provider": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_import_project_from_semicolon_csv(self, session_client, workspace):
        csv_content = CSVFormatter(delimiter=";").encode(
            [
                {
                    "name": "Imported Semicolon",
                    "identifier": "ISM",
                    "description": "From semicolon CSV",
                }
            ]
        )
        url = reverse("import-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "file": SimpleUploadedFile("project.csv", csv_content.encode("utf-8"), content_type="text/csv"),
                "provider": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(identifier="ISM", workspace=workspace)
        assert project.name == "Imported Semicolon"

    @pytest.mark.django_db
    def test_import_rejects_work_items_export_csv_with_helpful_message(self, session_client, workspace):
        csv_content = CSVFormatter().encode(
            [
                {
                    "project_name": "Some Project",
                    "project_identifier": "SP",
                    "state_name": "Todo",
                    "sequence_id": "SP-1",
                    "priority": "high",
                    "name": "This is a work item row",
                }
            ]
        )
        url = reverse("import-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "file": SimpleUploadedFile("issues.csv", csv_content.encode("utf-8"), content_type="text/csv"),
                "provider": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "wygląda na eksport elementów roboczych" in response.data["payload"].lower()


@pytest.mark.contract
class TestProjectCsvExportAPI:
    @pytest.mark.django_db
    def test_export_project_csv_semicolon_roundtrip(self, session_client, workspace, project):
        url = reverse("export-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {"provider": "csv", "delimiter": ";", "project": [str(project.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.content.decode("utf-8-sig")
        rows = CSVFormatter(delimiter=";").decode(body)
        assert rows[0]["identifier"] == "EXP"

    @pytest.mark.django_db
    def test_export_project_csv_roundtrip(self, session_client, workspace, project):
        url = reverse("export-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {"provider": "csv", "project": [str(project.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")
        body = response.content.decode("utf-8-sig")
        rows = CSVFormatter().decode(body)
        assert rows[0]["name"] == "Export Source"
        assert rows[0]["identifier"] == "EXP"

    @pytest.mark.django_db
    def test_export_project_xlsx(self, session_client, workspace, project):
        url = reverse("export-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {"provider": "xlsx", "project": [str(project.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert response.content[:2] == b"PK"
        assert response["Content-Disposition"].endswith('.xlsx"')

    @pytest.mark.django_db
    def test_export_project_rejects_unsupported_provider(self, session_client, workspace, project):
        url = reverse("export-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {"provider": "json", "project": [str(project.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestProjectFullZipImportExportAPI:
    @pytest.mark.django_db
    def test_export_and_import_full_project_csv(self, session_client, workspace, project, create_user):
        from plane.db.models import Issue, IssueSequence, State

        state = State.objects.filter(project=project, deleted_at__isnull=True).first()
        if state is None:
            state = State.objects.create(
                name="Todo",
                color="#3B82F6",
                project=project,
                workspace=workspace,
                group="unstarted",
                sequence=10000,
                created_by=create_user,
            )

        parent = Issue.objects.create(
            name="Parent epic ticket",
            project=project,
            workspace=workspace,
            state=state,
            sequence_id=1,
            sort_order=10000,
            priority="high",
            description_html="<p>Parent</p>",
            created_by=create_user,
        )
        child = Issue.objects.create(
            name="Child task",
            project=project,
            workspace=workspace,
            state=state,
            sequence_id=2,
            sort_order=20000,
            priority="medium",
            description_html="<p>Child</p>",
            parent=parent,
            created_by=create_user,
        )
        IssueSequence.objects.bulk_create(
            [
                IssueSequence(issue=parent, sequence=1, project=project, workspace=workspace),
                IssueSequence(issue=child, sequence=2, project=project, workspace=workspace),
            ]
        )

        export_url = reverse("export-projects", kwargs={"slug": workspace.slug})
        export_response = session_client.post(
            export_url,
            {
                "provider": "csv",
                "project": [str(project.id)],
                "include_work_items": True,
            },
            format="json",
        )

        assert export_response.status_code == status.HTTP_200_OK
        assert "text/csv" in export_response["Content-Type"]
        export_body = export_response.content.decode("utf-8-sig")
        assert "row_type" in export_body.lower() or "Row Type" in export_body

        import_url = reverse("import-projects", kwargs={"slug": workspace.slug})
        import_response = session_client.post(
            import_url,
            {
                "file": SimpleUploadedFile(
                    "project-full.csv",
                    export_response.content,
                    content_type="text/csv",
                ),
                "provider": "csv",
            },
            format="multipart",
        )

        assert import_response.status_code == status.HTTP_201_CREATED
        assert import_response.data["projects"][0]["created_work_items"] == 2
        cloned = Project.objects.get(id=import_response.data["projects"][0]["project_id"])
        assert Issue.objects.filter(project=cloned, deleted_at__isnull=True).count() == 2
        cloned_child = Issue.objects.get(project=cloned, name="Child task")
        assert cloned_child.parent_id is not None
        assert cloned_child.parent.name == "Parent epic ticket"

    @pytest.mark.django_db
    def test_full_export_requires_single_project(self, session_client, workspace, project, create_user):
        second = Project.objects.create(
            name="Second",
            identifier="SEC",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=second, member=create_user, role=20, is_active=True)

        url = reverse("export-projects", kwargs={"slug": workspace.slug})
        response = session_client.post(
            url,
            {
                "provider": "csv",
                "project": [str(project.id), str(second.id)],
                "include_work_items": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
