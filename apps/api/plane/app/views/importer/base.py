import json

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import ExporterHistorySerializer
from plane.db.models import ExporterHistory, Workspace
from plane.utils.porters.importer import DataImporter
from plane.utils.project_configuration import create_project_from_payload, ensure_unique_project_identifier
from plane.utils.project_template_payload import (
    strip_member_references_for_import,
    validate_and_clean_project_payload,
)

from .. import BaseAPIView

MAX_IMPORT_ROWS = 50


def _detect_invalid_upload(content: bytes) -> str | None:
    if not content:
        return "CSV file is empty."
    # Microsoft OLE Compound Document (.xls) — often produced when Excel re-saves a CSV
    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return (
            "Plik wygląda na binarny Excel (.xls), a nie na CSV. "
            "Wyeksportuj ponownie konfigurację projektu jako CSV (przecinek lub średnik) "
            "i nie zapisuj pliku ponownie w Excelu przed importem."
        )
    # ZIP-based Office Open XML (.xlsx)
    if content[:2] == b"PK":
        return (
            "Plik wygląda na Excel (.xlsx). Import konfiguracji projektu akceptuje tylko CSV. "
            "Wyeksportuj projekt ponownie w formacie CSV."
        )
    return None


class ImportProjectsEndpoint(BaseAPIView):
    model = ExporterHistory
    serializer_class = ExporterHistorySerializer

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        upload = request.FILES.get("file")
        provider = request.data.get("provider", "csv")

        if provider != "csv":
            return Response(
                {"error": f"Provider '{provider}' is not supported for project import."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload is None:
            return Response({"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        history = ExporterHistory.objects.create(
            workspace=workspace,
            project=[],
            initiated_by=request.user,
            provider="csv",
            type="project_imports",
            status="processing",
            name=upload.name,
        )

        try:
            content = upload.read()
            invalid_reason = _detect_invalid_upload(content)
            if invalid_reason:
                history.status = "failed"
                history.reason = invalid_reason
                history.save(update_fields=["status", "reason", "updated_at"])
                return Response({"error": invalid_reason}, status=status.HTTP_400_BAD_REQUEST)

            rows = DataImporter(format_type="csv").decode(content)
        except Exception as exc:
            history.status = "failed"
            history.reason = str(exc)
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {
                    "error": (
                        "Nie udało się odczytać pliku CSV. Upewnij się, że to eksport konfiguracji projektu "
                        "(nie eksport work itemów) i że plik nie był ponownie zapisywany w Excelu."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not rows:
            history.status = "failed"
            history.reason = "CSV file is empty."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response({"error": "CSV file is empty."}, status=status.HTTP_400_BAD_REQUEST)

        if len(rows) > MAX_IMPORT_ROWS:
            history.status = "failed"
            history.reason = f"CSV contains more than {MAX_IMPORT_ROWS} projects."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {"error": f"CSV cannot contain more than {MAX_IMPORT_ROWS} projects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_projects = []
        all_warnings: list[str] = []

        for index, row in enumerate(rows):
            try:
                payload, warnings = strip_member_references_for_import(row, workspace)
                cleaned = validate_and_clean_project_payload(payload, workspace, require_identity=True)
                cleaned["identifier"] = ensure_unique_project_identifier(
                    workspace, cleaned["identifier"], warnings
                )
                result = create_project_from_payload(
                    workspace=workspace,
                    user=request.user,
                    payload=cleaned,
                    warnings=warnings,
                )
                created_projects.append(result)
                all_warnings.extend(result.get("warnings", []))
            except ValidationError as exc:
                history.status = "failed"
                history.reason = json.dumps(exc.detail)
                history.save(update_fields=["status", "reason", "updated_at"])
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
            except ValueError as exc:
                history.status = "failed"
                history.reason = json.dumps(exc.args[0]) if exc.args else str(exc)
                history.save(update_fields=["status", "reason", "updated_at"])
                detail = exc.args[0] if exc.args else "Import failed."
                if isinstance(detail, dict):
                    return Response({**detail, "row": index + 1}, status=status.HTTP_400_BAD_REQUEST)
                return Response(
                    {"error": detail, "row": index + 1},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        history.status = "completed"
        history.project = [item["project_id"] for item in created_projects]
        history.reason = ""
        history.save(update_fields=["status", "project", "reason", "updated_at"])

        return Response(
            {
                "message": "Project import completed.",
                "projects": created_projects,
                "warnings": all_warnings,
                "history_id": str(history.id),
            },
            status=status.HTTP_201_CREATED,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        importer_history = ExporterHistory.objects.filter(
            workspace__slug=slug,
            type="project_imports",
        ).select_related("workspace", "initiated_by")

        if request.GET.get("per_page", False) and request.GET.get("cursor", False):
            return self.paginate(
                order_by=request.GET.get("order_by", "-created_at"),
                request=request,
                queryset=importer_history,
                on_results=lambda rows: ExporterHistorySerializer(rows, many=True).data,
            )

        return Response(
            {"error": "per_page and cursor are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
