import pytest

from plane.db.models import DEFAULT_STATES, Label, Project, ProjectMember, State
from plane.utils.project_configuration import (
    _create_states_from_templates,
    create_project_from_payload,
    ensure_unique_project_identifier,
)
from plane.utils.project_template_payload import strip_member_references_for_import, validate_and_clean_project_payload


@pytest.mark.django_db
class TestProjectConfiguration:
    def test_create_project_deduplicates_states(self, workspace, create_user):
        payload = validate_and_clean_project_payload(
            {
                "name": "Deduped",
                "identifier": "DED",
                "state_templates": [{"name": state["name"], "group": state["group"]} for state in DEFAULT_STATES]
                + [{"name": "Custom", "group": "started"}],
            },
            workspace,
            require_identity=True,
        )

        result = create_project_from_payload(workspace=workspace, user=create_user, payload=payload)
        project = Project.objects.get(id=result["project_id"])

        assert State.objects.filter(project=project, deleted_at__isnull=True).count() == len(DEFAULT_STATES) + 1
        assert result["created_states"] == 1

    def test_ensure_unique_project_identifier_suffixes_on_conflict(self, workspace, create_user):
        Project.objects.create(
            name="Existing",
            identifier="KOMP",
            workspace=workspace,
            created_by=create_user,
        )
        warnings: list[str] = []
        assert ensure_unique_project_identifier(workspace, "KOMP", warnings) == "KOMP2"
        assert warnings

    def test_strip_member_references_for_import(self, workspace, create_user):
        outsider_id = "00000000-0000-0000-0000-000000000099"
        payload = {"project_lead": outsider_id, "default_assignee": str(create_user.id)}
        cleaned, warnings = strip_member_references_for_import(payload, workspace)

        assert cleaned["project_lead"] is None
        assert cleaned["default_assignee"] == str(create_user.id)
        assert any("project_lead" in warning for warning in warnings)

    def test_create_states_from_templates_skips_existing_names(self, workspace, create_user):
        project = Project.objects.create(
            name="State test",
            identifier="STT",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
        State.objects.create(
            name="Todo",
            color="#000000",
            project=project,
            workspace=workspace,
            group="unstarted",
            sequence=1000,
            created_by=create_user,
        )

        created = _create_states_from_templates(
            project,
            [{"name": "Todo", "group": "unstarted"}, {"name": "QA", "group": "started"}],
            create_user.id,
        )

        assert created == 1
        assert State.objects.filter(project=project, name="QA").exists()
