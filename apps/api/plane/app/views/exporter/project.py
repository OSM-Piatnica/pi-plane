from rest_framework import status

from rest_framework.response import Response

from django.http import HttpResponse



from plane.app.permissions import ROLE, allow_permission

from plane.app.serializers import ExporterHistorySerializer

from plane.db.models import ExporterHistory, Project, Workspace

from plane.utils.porters.formatters import CSVFormatter, XLSXFormatter

from plane.utils.porters.serializers.project import serialize_project_export_payload



from .. import BaseAPIView





class ExportProjectsEndpoint(BaseAPIView):

    model = ExporterHistory

    serializer_class = ExporterHistorySerializer



    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")

    def post(self, request, slug):

        workspace = Workspace.objects.get(slug=slug)

        provider = request.data.get("provider", "csv")

        delimiter = request.data.get("delimiter", ",")

        project_ids = request.data.get("project", [])



        if provider not in ["csv", "xlsx"]:

            return Response(

                {"error": f"Provider '{provider}' is not supported for project export."},

                status=status.HTTP_400_BAD_REQUEST,

            )



        if provider == "csv" and delimiter not in [",", ";"]:

            delimiter = ","



        if not project_ids:

            return Response(

                {"error": "At least one project id is required."},

                status=status.HTTP_400_BAD_REQUEST,

            )



        projects = Project.objects.filter(

            id__in=project_ids,

            workspace_id=workspace.id,

            archived_at__isnull=True,

            deleted_at__isnull=True,

            project_projectmember__member=request.user,

            project_projectmember__is_active=True,

        ).distinct()



        if not projects.exists():

            return Response({"error": "No accessible projects found."}, status=status.HTTP_400_BAD_REQUEST)



        rows = [serialize_project_export_payload(project) for project in projects]



        if provider == "xlsx":

            file_content = XLSXFormatter().encode(rows)

            extension = "xlsx"

            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            response = HttpResponse(file_content, content_type=content_type)

        else:

            file_content = CSVFormatter(delimiter=delimiter).encode(rows)

            extension = "csv"

            response = HttpResponse(file_content, content_type="text/csv; charset=utf-8")



        history = ExporterHistory.objects.create(

            workspace=workspace,

            project=[str(project_id) for project_id in projects.values_list("id", flat=True)],

            initiated_by=request.user,

            provider=provider,

            type="project_exports",

            status="completed",

            name=f"{slug}-projects.{extension}",

        )



        filename = f"{slug}-projects-{history.token[:6]}.{extension}"

        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        response["X-Export-History-Id"] = str(history.id)

        return response



    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")

    def get(self, request, slug):

        exporter_history = ExporterHistory.objects.filter(

            workspace__slug=slug,

            type="project_exports",

        ).select_related("workspace", "initiated_by")



        if request.GET.get("per_page", False) and request.GET.get("cursor", False):

            return self.paginate(

                order_by=request.GET.get("order_by", "-created_at"),

                request=request,

                queryset=exporter_history,

                on_results=lambda rows: ExporterHistorySerializer(rows, many=True).data,

            )



        return Response(

            {"error": "per_page and cursor are required"},

            status=status.HTTP_400_BAD_REQUEST,

        )


