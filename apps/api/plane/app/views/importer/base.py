import io
import json
import zipfile

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import ExporterHistorySerializer
from plane.db.models import ExporterHistory, Project, Workspace
from plane.utils.porters.importer import DataImporter
from plane.utils.project_configuration import create_project_from_payload, ensure_unique_project_identifier
from plane.utils.project_csv_package import split_import_rows
from plane.utils.project_template_payload import (
    strip_member_references_for_import,
    validate_and_clean_project_payload,
)
from plane.utils.project_work_item_import import MAX_WORK_ITEMS_IMPORT, import_work_items_into_project

from .. import BaseAPIView

MAX_IMPORT_ROWS = 50
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def _is_ole_compound(content: bytes) -> bool:
    return content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _is_zip_bytes(content: bytes) -> bool:
    return content[:2] == b"PK"


def _is_xlsx_archive(content: bytes) -> bool:
    if not _is_zip_bytes(content):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            return "[Content_Types].xml" in names or any(name.startswith("xl/") for name in names)
    except zipfile.BadZipFile:
        return False


def _extract_legacy_project_package(content: bytes) -> tuple[list[dict], list[dict] | None]:
    """Extract project and work-item rows from a legacy ZIP package."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = {name: name for name in archive.namelist()}
        project_name = next(
            (name for name in names if name.replace("\\", "/").split("/")[-1].lower() == "project.csv"),
            None,
        )
        work_items_name = next(
            (name for name in names if name.replace("\\", "/").split("/")[-1].lower() == "work_items.csv"),
            None,
        )
        if not project_name:
            raise ValueError(
                {
                    "error": (
                        "ZIP must contain project.csv. "
                        "Use a single full-project CSV export or a configuration CSV."
                    )
                }
            )
        project_bytes = archive.read(project_name)
        project_rows = DataImporter(format_type="csv").decode(project_bytes)
        work_item_rows = None
        if work_items_name:
            work_item_bytes = archive.read(work_items_name)
            work_item_rows = DataImporter(format_type="csv").decode(work_item_bytes)
        return project_rows, work_item_rows


class ImportProjectsEndpoint(BaseAPIView):
    model = ExporterHistory
    serializer_class = ExporterHistorySerializer

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        upload = request.FILES.get("file")
        provider = request.data.get("provider", "csv")

        if provider not in ["csv", "zip"]:
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
            if len(content) > MAX_UPLOAD_BYTES:
                history.status = "failed"
                history.reason = "File too large."
                history.save(update_fields=["status", "reason", "updated_at"])
                return Response(
                    {"error": f"File must be smaller than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if _is_ole_compound(content):
                reason = (
                    "Plik wygląda na binarny Excel (.xls), a nie na CSV. "
                    "Użyj eksportu Plane i nie zapisuj pliku ponownie w Excelu przed importem."
                )
                history.status = "failed"
                history.reason = reason
                history.save(update_fields=["status", "reason", "updated_at"])
                return Response({"error": reason}, status=status.HTTP_400_BAD_REQUEST)

            work_item_rows = None
            if _is_zip_bytes(content):
                if _is_xlsx_archive(content):
                    reason = (
                        "Plik wygląda na Excel (.xlsx). "
                        "Import wymaga jednego pliku CSV (konfiguracja albo pełny projekt z work items)."
                    )
                    history.status = "failed"
                    history.reason = reason
                    history.save(update_fields=["status", "reason", "updated_at"])
                    return Response({"error": reason}, status=status.HTTP_400_BAD_REQUEST)
                rows, work_item_rows = _extract_legacy_project_package(content)
            else:
                decoded_rows = DataImporter(format_type="csv").decode(content)
                rows, work_item_rows = split_import_rows(decoded_rows)
        except ValueError as exc:
            detail = exc.args[0] if exc.args else "Invalid package."
            history.status = "failed"
            history.reason = json.dumps(detail) if not isinstance(detail, str) else detail
            history.save(update_fields=["status", "reason", "updated_at"])
            if isinstance(detail, dict):
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            history.status = "failed"
            history.reason = str(exc)
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {
                    "error": (
                        "Nie udało się odczytać pliku. Upewnij się, że to eksport Plane (CSV) "
                        "z konfiguracją projektu albo pełnym projektem (config + work items)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not rows:
            history.status = "failed"
            history.reason = "CSV file is empty."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response({"error": "CSV file is empty."}, status=status.HTTP_400_BAD_REQUEST)

        if work_item_rows is not None and len(rows) != 1:
            history.status = "failed"
            history.reason = "Full project CSV must contain exactly one project row."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {"error": "Full project CSV must contain exactly one project row."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(rows) > MAX_IMPORT_ROWS:
            history.status = "failed"
            history.reason = f"CSV contains more than {MAX_IMPORT_ROWS} projects."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {"error": f"CSV cannot contain more than {MAX_IMPORT_ROWS} projects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if work_item_rows is not None and len(work_item_rows) > MAX_WORK_ITEMS_IMPORT:
            history.status = "failed"
            history.reason = f"CSV exceeds {MAX_WORK_ITEMS_IMPORT} work item rows."
            history.save(update_fields=["status", "reason", "updated_at"])
            return Response(
                {"error": f"CSV cannot contain more than {MAX_WORK_ITEMS_IMPORT} work items."},
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

                if work_item_rows is not None:
                    project = Project.objects.get(id=result["project_id"])
                    wi_result = import_work_items_into_project(
                        project=project,
                        user=request.user,
                        rows=work_item_rows,
                        warnings=result.get("warnings") or [],
                    )
                    result["created_work_items"] = wi_result["created_work_items"]
                    result["warnings"] = wi_result["warnings"]
                else:
                    result["created_work_items"] = 0

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
