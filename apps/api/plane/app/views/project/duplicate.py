# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the project duplication of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

# Python imports
import logging
import uuid

# Third party imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import ProjectListSerializer
from plane.app.serializers.project_duplicate import ProjectCopyJobSerializer, ProjectDuplicateSerializer
from plane.app.views.base import BaseAPIView
from plane.app.views.project.base import ProjectViewSet
from plane.bgtasks.project_add_user_email_task import project_add_user_email
from plane.bgtasks.project_copy_task import copy_project_work_items
from plane.bgtasks.webhook_task import model_activity
from plane.db.models import FileAsset, Project, ProjectCopyJob, WorkspaceMember
from plane.db.models.project_copy_job import ACTIVE_STATUSES
from plane.settings.storage import get_storage
from plane.utils.host import base_host
from plane.utils.path_validator import sanitize_filename
from plane.utils.project_duplicate import ProjectCopyError, duplicate_project

log = logging.getLogger(__name__)


def _copy_cover_image(request, source_asset_id, target):
    """Copy the source project's cover into the new project.

    Runs after the copy transaction has committed, because an S3 object copy
    cannot be rolled back with it. A cover that cannot be copied is not worth
    failing a project over, so this degrades to no cover and says so.

    The asset row is created per project: `cover_image_asset` is a single
    foreign key, so sharing the row would make deleting either project take the
    other's cover with it.
    """
    if source_asset_id is None:
        return None

    original = FileAsset.objects.filter(id=source_asset_id, is_uploaded=True, workspace=target.workspace).first()
    if original is None:
        return "cover_image:unreadable"

    try:
        name = (original.attributes or {}).get("name")
        destination_key = f"{target.workspace_id}/{uuid.uuid4().hex}-{sanitize_filename(name) or 'unnamed'}"
        if get_storage(request=request).copy_object(original.asset.name, destination_key) is None:
            return "cover_image:failed"

        duplicated = FileAsset.objects.create(
            attributes={
                "name": name,
                "type": (original.attributes or {}).get("type"),
                "size": (original.attributes or {}).get("size"),
            },
            asset=destination_key,
            size=original.size,
            workspace_id=target.workspace_id,
            created_by_id=request.user.id,
            entity_type=FileAsset.EntityTypeContext.PROJECT_COVER,
            project_id=target.id,
            storage_metadata=original.storage_metadata,
            is_uploaded=True,
        )
    except Exception:
        log.warning("Could not copy the cover image for project %s", target.id, exc_info=True)
        return "cover_image:failed"

    Project.objects.filter(pk=target.pk).update(cover_image_asset=duplicated)
    return None


class ProjectDuplicateUserThrottle(SimpleRateThrottle):
    scope = "project_duplicate_user"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class ProjectDuplicateWorkspaceThrottle(SimpleRateThrottle):
    """Per-workspace, because the cost lands on the workspace row's lock.

    One user staying under their own limit can still stall project creation for
    everyone else in the workspace, so the two throttles are not redundant.
    """

    scope = "project_duplicate_workspace"

    def get_cache_key(self, request, view):
        slug = view.kwargs.get("slug")
        if not slug:
            return None
        return self.cache_format % {"scope": self.scope, "ident": slug}


class ProjectDuplicateEndpoint(BaseAPIView):
    """Copy a project's configuration into a new project.

    The source project id is carried in the URL rather than the body on purpose:
    ``allow_permission`` resolves its subject from ``kwargs["project_id"]``, so a
    body-supplied source would leave this endpoint with no project-level check
    at all while it reads the source's entire object graph.
    """

    throttle_classes = [ProjectDuplicateUserThrottle, ProjectDuplicateWorkspaceThrottle]

    # ADMIN of the source, not MEMBER. The copy re-links the source's work item
    # types, which are workspace-wide definitions shared with other projects, and
    # the caller becomes ADMIN of the copy. Allowing a mere MEMBER to duplicate
    # would hand them admin control over definitions of projects they do not
    # administer.
    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def post(self, request, slug, project_id):
        # `allow_permission` at PROJECT level proves the caller is an active
        # member of the *source*, which is what stops a workspace member reading
        # a project whose network is SECRET. It says nothing about whether they
        # may create a project, which `ProjectViewSet.create` gates separately at
        # workspace level -- so check that too. The two are independent.
        if not WorkspaceMember.objects.filter(
            member=request.user,
            workspace__slug=slug,
            role__in=[ROLE.ADMIN.value, ROLE.MEMBER.value],
            is_active=True,
        ).exists():
            return Response({"error": "You don't have the required permissions."}, status=status.HTTP_403_FORBIDDEN)

        source = Project.objects.filter(pk=project_id, workspace__slug=slug).first()
        if source is None:
            return Response({"error": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProjectDuplicateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payload = serializer.validated_data

        # One work item copy per workspace at a time. The size cap bounds a single copy; this is what
        # stops one person queueing ten large ones and holding a worker for an hour. Only checked when
        # work items were asked for -- a configuration copy is bounded and cheap.
        if (payload.get("include") or {}).get("work_items") and ProjectCopyJob.objects.filter(
            workspace__slug=slug, status__in=ACTIVE_STATUSES
        ).exists():
            return Response({"error": "PROJECT_COPY_ALREADY_RUNNING"}, status=status.HTTP_409_CONFLICT)

        try:
            result = duplicate_project(
                source=source,
                actor=request.user,
                name=payload.get("name"),
                identifier=payload.get("identifier"),
                network=payload.get("network"),
                options=payload.get("include"),
                work_item_properties=payload.get("work_item_properties"),
            )
        except ProjectCopyError as error:
            body = {"error": error.code}
            if error.detail is not None:
                body["detail"] = error.detail
            return Response(body, status=error.status_code)

        # Everything from here runs after `duplicate_project` has committed, so
        # the project exists whatever happens next. Reporting a failure now
        # would tell the caller the copy did not happen when it did -- so each
        # side effect is allowed to fail on its own and is reported in
        # `copy_summary.skipped`.
        cover_note = _copy_cover_image(request, result.cover_source_asset_id, result.project)
        if cover_note:
            result.skipped.append(cover_note)

        # Tell the people the copy enrolled, the same way `ProjectMemberViewSet`
        # does. Nobody is mailed about a project that rolled back.
        for member_id in result.notify_member_ids:
            try:
                project_add_user_email.delay(base_host(request=request, is_app=True), member_id, request.user.id)
            except Exception:
                log.warning("Could not queue the project-added email for %s", member_id, exc_info=True)
                result.skipped.append("members:not-notified")
                break

        try:
            model_activity.delay(
                model_name="project",
                model_id=str(result.project.id),
                requested_data=request.data,
                current_instance=None,
                actor_id=request.user.id,
                slug=slug,
                origin=base_host(request=request, is_app=True),
            )
        except Exception:
            log.warning("Could not queue the creation activity for project %s", result.project.id, exc_info=True)

        # Dispatched here rather than inside the service, for the same reason the cover image is: the job
        # reads rows that only exist once the transaction has committed. A broker failure is not fatal --
        # the job row is already queued, and `reclaim_stalled_project_copies` picks up anything that was
        # never delivered.
        if result.work_item_job_id is not None:
            try:
                copy_project_work_items.delay(str(result.work_item_job_id))
            except Exception:
                log.warning(
                    "Could not queue the work item copy for project %s; the sweeper will retry",
                    result.project.id,
                    exc_info=True,
                )

        # Same queryset (and so the same shape) `ProjectViewSet.create` answers
        # with, so the web store can treat the two identically.
        viewset = ProjectViewSet()
        viewset.request = request
        viewset.kwargs = {"slug": slug}
        created = viewset.get_queryset().filter(pk=result.project.id).first()
        data = ProjectListSerializer(created).data
        data["copy_summary"] = {
            "source_project_id": str(source.id),
            "counts": result.counts,
            "skipped": result.skipped,
        }
        if result.work_item_job_id is not None:
            data["copy_summary"]["work_items"] = {
                "job_id": str(result.work_item_job_id),
                "status": ProjectCopyJob.Status.QUEUED,
                "total": result.counts.get("work_items_planned", 0),
                "copied": 0,
            }
        return Response(data, status=status.HTTP_201_CREATED)


class ProjectCopyStatusEndpoint(BaseAPIView):
    """How far the work item copy of this project has got.

    Keyed on the *target* project rather than the job id, because that is what the client has: the
    duplicate form navigates straight to the copy, and a page reload loses any id held in memory. It
    also means the read is authorised exactly like every other project read, with no new surface.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def get(self, request, slug, project_id):
        job = ProjectCopyJob.objects.filter(target_project_id=project_id, workspace__slug=slug).first()
        if job is None:
            # Most projects were never copied; that is not an error.
            return Response({"job": None}, status=status.HTTP_200_OK)
        return Response({"job": ProjectCopyJobSerializer(job).data}, status=status.HTTP_200_OK)


class ProjectCopyRetryEndpoint(BaseAPIView):
    """Ask a failed copy to carry on from where it stopped.

    Resuming is safe because every pass skips what is already present, so a retry adds what is missing
    rather than a second copy of what is not. Only a failed job can be retried; a running one already
    has a worker, and the sweeper covers one whose worker died.
    """

    @allow_permission([ROLE.ADMIN], level="PROJECT")
    def post(self, request, slug, project_id):
        job = ProjectCopyJob.objects.filter(target_project_id=project_id, workspace__slug=slug).first()
        if job is None:
            return Response({"error": "No copy has been run for this project."}, status=status.HTTP_404_NOT_FOUND)
        if job.status != ProjectCopyJob.Status.FAILED:
            return Response({"error": "PROJECT_COPY_NOT_RETRYABLE"}, status=status.HTTP_409_CONFLICT)

        job.status = ProjectCopyJob.Status.QUEUED
        job.reason = ""
        job.completed_at = None
        job.attempt_count = 0
        job.save(update_fields=["status", "reason", "completed_at", "attempt_count", "updated_at"])

        try:
            copy_project_work_items.delay(str(job.id))
        except Exception:
            log.warning("Could not queue the retry for copy job %s; the sweeper will retry", job.id, exc_info=True)

        return Response({"job": ProjectCopyJobSerializer(job).data}, status=status.HTTP_200_OK)
