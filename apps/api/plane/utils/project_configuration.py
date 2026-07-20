from django.db import IntegrityError

from plane.app.permissions import ROLE
from plane.app.serializers import ProjectSerializer
from plane.db.models import DEFAULT_STATES, Label, Project, ProjectMember, State, Workspace
from plane.utils.project_template_issue_types import seed_project_issue_types_from_template_payload

PROJECT_FIELD_KEYS = {
    "name",
    "identifier",
    "description",
    "start_date",
    "target_date",
    "network",
    "project_lead",
    "default_assignee",
    "logo_props",
    "cover_image_url",
    "cycle_view",
    "module_view",
    "issue_views_view",
    "page_view",
    "intake_view",
    "is_time_tracking_enabled",
    "is_issue_type_enabled",
    "guest_view_all_features",
}

IDENTIFIER_MAX_LENGTH = 12


def ensure_unique_project_identifier(workspace: Workspace, identifier: str, warnings: list[str]) -> str:
    """Return an available project identifier, suffixing when the original is taken."""
    base = (identifier or "").strip().upper()
    if not base:
        return base

    exists = Project.objects.filter(
        workspace_id=workspace.id,
        identifier=base,
        deleted_at__isnull=True,
    ).exists()
    if not exists:
        return base

    for index in range(2, 100):
        suffix = str(index)
        trimmed = base[: IDENTIFIER_MAX_LENGTH - len(suffix)]
        candidate = f"{trimmed}{suffix}"
        if not Project.objects.filter(
            workspace_id=workspace.id,
            identifier=candidate,
            deleted_at__isnull=True,
        ).exists():
            warnings.append(
                f'Identifier "{base}" already exists in this workspace; imported as "{candidate}".'
            )
            return candidate

    raise ValueError(
        {
            "error": (
                f'Project identifier "{base}" already exists and no free suffix was found. '
                "Change the Identifier column in the CSV and try again."
            )
        }
    )


def _project_data_from_payload(payload: dict) -> dict:
    data = {key: payload[key] for key in PROJECT_FIELD_KEYS if key in payload}
    cover_image_url = data.pop("cover_image_url", None)
    if cover_image_url:
        data["cover_image"] = cover_image_url
    return data


def _create_states_from_templates(project: Project, state_templates: list[dict], user_id) -> int:
    if not state_templates:
        return 0

    existing_names = {
        name.lower()
        for name in State.objects.filter(project_id=project.id, deleted_at__isnull=True).values_list("name", flat=True)
    }
    created = 0
    max_sequence = (
        State.objects.filter(project_id=project.id, deleted_at__isnull=True).order_by("-sequence").values_list(
            "sequence", flat=True
        ).first()
        or 0
    )

    for state in state_templates:
        name = str(state.get("name", "")).strip()
        if not name or name.lower() in existing_names:
            continue
        try:
            State.objects.create(
                name=name[:255],
                color=state.get("color") or "#60646C",
                project=project,
                workspace=project.workspace,
                group=state.get("group") or "unstarted",
                default=bool(state.get("default", False)),
                sequence=max_sequence + 10000,
                created_by_id=user_id,
            )
            existing_names.add(name.lower())
            max_sequence += 10000
            created += 1
        except IntegrityError:
            existing_names.add(name.lower())

    return created


def _create_labels_from_templates(project: Project, label_templates: list[dict], user_id) -> int:
    if not label_templates:
        return 0

    existing_names = {
        name.lower()
        for name in Label.objects.filter(project_id=project.id, deleted_at__isnull=True).values_list("name", flat=True)
    }
    created = 0
    max_sort = (
        Label.objects.filter(project_id=project.id, deleted_at__isnull=True).order_by("-sort_order").values_list(
            "sort_order", flat=True
        ).first()
        or 0
    )

    for label in label_templates:
        name = str(label.get("name", "")).strip()
        if not name or name.lower() in existing_names:
            continue
        try:
            Label.objects.create(
                name=name[:255],
                color=label.get("color") or "#858585",
                project=project,
                workspace=project.workspace,
                sort_order=max_sort + 10000,
                created_by_id=user_id,
            )
            existing_names.add(name.lower())
            max_sort += 10000
            created += 1
        except IntegrityError:
            existing_names.add(name.lower())

    return created


def create_project_from_payload(
    *,
    workspace: Workspace,
    user,
    payload: dict,
    warnings: list[str] | None = None,
) -> dict:
    project_data = _project_data_from_payload(payload)
    serializer = ProjectSerializer(data=project_data, context={"workspace_id": workspace.id})
    if not serializer.is_valid():
        raise ValueError(serializer.errors)

    project = serializer.save()
    ProjectMember.objects.create(
        project_id=project.id,
        member=user,
        role=ROLE.ADMIN.value,
    )

    lead_id = payload.get("project_lead")
    if lead_id and str(lead_id) != str(user.id):
        ProjectMember.objects.get_or_create(
            project_id=project.id,
            member_id=lead_id,
            defaults={"role": ROLE.ADMIN.value, "is_active": True},
        )

    State.objects.bulk_create(
        [
            State(
                name=state["name"],
                color=state["color"],
                project=project,
                sequence=state["sequence"],
                workspace=project.workspace,
                group=state["group"],
                default=state.get("default", False),
                created_by=user,
            )
            for state in DEFAULT_STATES
        ]
    )

    created_states = _create_states_from_templates(project, payload.get("state_templates") or [], user.id)
    created_labels = _create_labels_from_templates(project, payload.get("label_templates") or [], user.id)

    if payload.get("is_issue_type_enabled"):
        seed_project_issue_types_from_template_payload(
            project=project,
            payload=payload,
            created_by_id=user.id,
        )

    return {
        "project_id": str(project.id),
        "project_identifier": project.identifier,
        "project_name": project.name,
        "created_states": created_states,
        "created_labels": created_labels,
        "warnings": warnings or [],
    }
