# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Python imports
import json

# Django imports
from django.utils import timezone
from django.db.models import Q, OuterRef, F, Func, UUIDField, Value, CharField, Subquery
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.utils.work_item_edit_rule import restrict_work_item_changes
from plane.app.serializers import IssueRelationSerializer, RelatedIssueSerializer
from plane.app.permissions import ProjectEntityPermission
from plane.db.models import (
    Project,
    IssueRelation,
    Issue,
    FileAsset,
    IssueLink,
    CycleIssue,
)
from plane.bgtasks.issue_activities_task import issue_activity
from plane.utils.issue_relation_constraints import TIMELINE_RELATION_TYPES
from plane.utils.issue_relation_mapper import get_actual_relation
from plane.utils.issue_relation_service import (
    existing_relation_others,
    existing_symmetric_pairs,
    parse_lag,
    relation_ends,
    set_lag,
    validate_new_relation,
)
from plane.utils.relation_type_toggles import relation_type_disabled_error
from plane.utils.issue_relation_types import ALL_RELATION_NAMES, is_mirrored, is_symmetric
from plane.utils.host import base_host


def issue_in_project(issue_id, slug, project_id, *, include_archived=False):
    """Whether ``issue_id`` belongs to the URL workspace + project.

    ``ProjectEntityPermission`` only checks that the caller is a member of the URL's
    ``project_id`` — it never binds the sibling ``issue_id`` path parameter to that
    project. Every handler taking both must therefore check this itself, or it is
    reachable cross-project/cross-tenant.

    ``Issue.issue_objects`` (the default) additionally excludes archived/draft/triage
    issues, which is correct for the write paths below — but a read path like
    ``list()`` must still find archived issues in the URL's own project, the same way
    ``IssueViewSet.retrieve()`` does with ``Issue.objects``. Pass
    ``include_archived=True`` for that case; the project/workspace binding itself is
    unchanged either way.
    """
    manager = Issue.objects if include_archived else Issue.issue_objects
    return manager.filter(pk=issue_id, workspace__slug=slug, project_id=project_id).exists()


def related_issue_lags(issue_relations, issue_id, name):
    """``{id: lag_days}`` of the work items that stand in relation ``name`` to ``issue_id``, read from either side."""
    stored = get_actual_relation(name)
    if is_symmetric(name):
        pairs = list(
            issue_relations.filter(issue_id=issue_id, relation_type=stored).values_list("related_issue_id", "lag_days")
        ) + list(
            issue_relations.filter(related_issue_id=issue_id, relation_type=stored).values_list("issue_id", "lag_days")
        )
    elif is_mirrored(name):
        # the row is stored from the other work item: "blocking" is "blocked_by" with this item as the related side
        pairs = list(
            issue_relations.filter(related_issue_id=issue_id, relation_type=stored).values_list("issue_id", "lag_days")
        )
    else:
        pairs = list(
            issue_relations.filter(issue_id=issue_id, relation_type=stored).values_list("related_issue_id", "lag_days")
        )
    return dict(pairs)


class IssueRelationViewSet(BaseViewSet):
    serializer_class = IssueRelationSerializer
    model = IssueRelation
    permission_classes = [ProjectEntityPermission]

    def list(self, request, slug, project_id, issue_id):
        # SECURITY: the read path needs the same binding as the writes below. Without
        # it a member of project A could list the relations of an issue in project B of
        # the same workspace and receive that issue's name, priority, assignees and
        # labels in the response.
        #
        # include_archived=True: this is a read, not a write, and the issue detail page
        # fetches relations unconditionally for archived issues too. Scoping this lookup
        # with the write-path's issue_objects (which excludes archived issues) would 404
        # a legitimate same-project read instead of only closing the cross-project hole.
        if not issue_in_project(issue_id, slug, project_id, include_archived=True):
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        issue_relations = (
            IssueRelation.objects.filter(Q(issue_id=issue_id) | Q(related_issue=issue_id))
            .filter(workspace__slug=self.kwargs.get("slug"))
            .select_related("project")
            .select_related("workspace")
            .select_related("issue")
            .order_by("-created_at")
            .distinct()
        )
        queryset = (
            Issue.issue_objects.filter(workspace__slug=slug)
            .select_related("workspace", "project", "state", "parent")
            .prefetch_related("assignees", "labels", "issue_module__module")
            .annotate(
                cycle_id=Subquery(
                    CycleIssue.objects.filter(issue=OuterRef("id"), deleted_at__isnull=True).values("cycle_id")[:1]
                )
            )
            .annotate(
                link_count=IssueLink.objects.filter(issue=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                attachment_count=FileAsset.objects.filter(
                    issue_id=OuterRef("id"),
                    entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
                )
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                sub_issues_count=Issue.issue_objects.filter(parent=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                label_ids=Coalesce(
                    ArrayAgg(
                        "labels__id",
                        distinct=True,
                        filter=Q(~Q(labels__id__isnull=True) & (Q(label_issue__deleted_at__isnull=True))),
                    ),
                    Value([], output_field=ArrayField(UUIDField())),
                ),
                assignee_ids=Coalesce(
                    ArrayAgg(
                        "assignees__id",
                        distinct=True,
                        filter=Q(
                            ~Q(assignees__id__isnull=True)
                            & Q(assignees__member_project__is_active=True)
                            & Q(issue_assignee__deleted_at__isnull=True)
                        ),
                    ),
                    Value([], output_field=ArrayField(UUIDField())),
                ),
            )
        ).distinct()

        # Fields
        fields = [
            "id",
            "name",
            "state_id",
            "sort_order",
            "priority",
            "sequence_id",
            "project_id",
            "label_ids",
            "assignee_ids",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "relation_type",
        ]

        response_data = {}
        for name in ALL_RELATION_NAMES:
            lags = related_issue_lags(issue_relations, issue_id, name)
            rows = list(
                queryset.filter(pk__in=list(lags))
                .annotate(relation_type=Value(name, output_field=CharField()))
                .values(*fields)
            )
            for row in rows:
                row["lag_days"] = lags.get(row["id"], 0)
            response_data[name] = rows

        return Response(response_data, status=status.HTTP_200_OK)

    @restrict_work_item_changes(param="issue_id")
    def create(self, request, slug, project_id, issue_id):
        relation_type = request.data.get("relation_type", None)
        if relation_type is None:
            return Response(
                {"message": "Issue relation type is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issues = request.data.get("issues", [])
        project = Project.objects.get(pk=project_id)

        # SECURITY: bind the URL issue to the workspace + project before using it as one
        # side of the relation. The body `issues` are scoped below, but `issue_id` came
        # straight from the URL — so the earlier scoping fix covered one side of the
        # relationship and missed the other.
        if not issue_in_project(issue_id, slug, project_id):
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        # Scope to workspace to prevent cross-tenant IDOR
        # Relations can cross projects so only workspace scope is enforced
        issues = list(
            Issue.issue_objects.filter(
                workspace__slug=slug,
                pk__in=issues,
            ).values_list("id", flat=True)
        )

        if relation_type not in ALL_RELATION_NAMES:
            return Response({"message": "Unknown issue relation type"}, status=status.HTTP_400_BAD_REQUEST)

        disabled_error = relation_type_disabled_error(project, relation_type)
        if disabled_error:
            return Response(disabled_error, status=status.HTTP_400_BAD_REQUEST)

        lag, lag_error = parse_lag(request.data.get("lag_days"), relation_type)
        if lag_error:
            return Response(lag_error, status=status.HTTP_400_BAD_REQUEST)

        current_issue = (
            Issue.objects.select_related("state", "project").filter(pk=issue_id, project_id=project_id).first()
        )
        if current_issue is None:
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        related_by_id = {
            str(item.id): item for item in Issue.objects.select_related("state", "project").filter(pk__in=issues)
        }
        for related_id in issues:
            related_issue = related_by_id.get(str(related_id))
            if related_issue is None:
                return Response(
                    {"error": f"Related work item {related_id} not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation_error = validate_new_relation(current_issue, related_issue, relation_type)
            if relation_error:
                return Response(relation_error, status=status.HTTP_400_BAD_REQUEST)
            if relation_type in TIMELINE_RELATION_TYPES:
                from plane.utils.issue_timeline_relation_validation import validate_new_timeline_relation

                timeline_error = validate_new_timeline_relation(current_issue, related_issue, relation_type, lag or 0)
                if timeline_error:
                    return Response(timeline_error, status=status.HTTP_400_BAD_REQUEST)

        # a symmetric relation that exists from the other side is not stored a second time
        already_related = existing_symmetric_pairs(relation_type, issue_id, issues)
        issues = [item for item in issues if str(item) not in already_related]

        already_there = existing_relation_others(issue_id, issues, relation_type)
        issue_relation = IssueRelation.objects.bulk_create(
            [
                IssueRelation(
                    issue_id=relation_ends(issue_id, issue, relation_type)[0],
                    related_issue_id=relation_ends(issue_id, issue, relation_type)[1],
                    relation_type=(get_actual_relation(relation_type)),
                    lag_days=lag or 0,
                    project_id=project_id,
                    workspace_id=project.workspace_id,
                    created_by=request.user,
                    updated_by=request.user,
                )
                for issue in issues
            ],
            batch_size=10,
            ignore_conflicts=True,
        )

        if lag is not None:
            # posting a relation that exists already with a lag changes its lag
            set_lag(issue_id, issues, relation_type, lag)

        new_issues = [item for item in issues if str(item) not in already_there]
        if new_issues:
            issue_activity.delay(
                type="issue_relation.activity.created",
                requested_data=json.dumps(
                    {"relation_type": relation_type, "issues": new_issues}, cls=DjangoJSONEncoder
                ),
                actor_id=str(request.user.id),
                issue_id=str(issue_id),
                project_id=str(project_id),
                current_instance=None,
                epoch=int(timezone.now().timestamp()),
                notification=True,
                origin=base_host(request=request, is_app=True),
            )

        if is_mirrored(relation_type):
            return Response(
                RelatedIssueSerializer(issue_relation, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                IssueRelationSerializer(issue_relation, many=True).data,
                status=status.HTTP_201_CREATED,
            )

    @restrict_work_item_changes(param="issue_id")
    def remove_relation(self, request, slug, project_id, issue_id):
        related_issue = request.data.get("related_issue", None)

        # SECURITY: same binding as create() — the URL issue must belong to the URL
        # project before it can be used to select a relation for deletion. Otherwise a
        # member of one project could delete relations between issues of a sibling
        # project in the same workspace. The IssueRelation row itself stays
        # workspace-scoped only: relations legitimately span projects, and either
        # participant's project may remove them.
        if not issue_in_project(issue_id, slug, project_id):
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        relation_type = request.data.get("relation_type", None)
        rows = IssueRelation.objects.filter(workspace__slug=slug).filter(
            Q(issue_id=related_issue, related_issue_id=issue_id) | Q(issue_id=issue_id, related_issue_id=related_issue)
        )
        if relation_type:
            if relation_type not in ALL_RELATION_NAMES:
                return Response({"message": "Unknown issue relation type"}, status=status.HTTP_400_BAD_REQUEST)
            # only this type, on the side it was added from; the other types between the two stay
            rows = rows.filter(relation_type=get_actual_relation(relation_type))
            if not is_symmetric(relation_type):
                source, related = relation_ends(issue_id, related_issue, relation_type)
                rows = rows.filter(issue_id=source, related_issue_id=related)
        elif rows.count() > 1:
            return Response(
                {"error": "These work items have more than one relation; say which one to remove (relation_type)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        issue_relations = rows.first()
        if issue_relations is None:
            # Previously fell through to `None.delete()` -> AttributeError -> 500.
            return Response({"error": "Issue relation not found"}, status=status.HTTP_404_NOT_FOUND)
        current_instance = json.dumps(IssueRelationSerializer(issue_relations).data, cls=DjangoJSONEncoder)
        issue_relations.delete()
        issue_activity.delay(
            type="issue_relation.activity.deleted",
            requested_data=json.dumps(request.data, cls=DjangoJSONEncoder),
            actor_id=str(request.user.id),
            issue_id=str(issue_id),
            project_id=str(project_id),
            current_instance=current_instance,
            epoch=int(timezone.now().timestamp()),
            notification=True,
            origin=base_host(request=request, is_app=True),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
