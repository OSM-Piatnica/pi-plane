# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import Count, Q

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.bgtasks.group_membership_notification_task import ADDED, ROLE_CHANGED, notify_group_membership
from plane.app.permissions import ROLE, WorkSpaceAdminPermission, WorkspaceViewerPermission, allow_permission
from plane.app.serializers.user_group import (
    DepartmentLiteSerializer,
    WorkspaceMemberDepartmentSerializer,
    UserGroupMemberSerializer,
    UserGroupMemberWriteSerializer,
    UserGroupSerializer,
)
from plane.db.models import (
    GroupKind,
    IssueGroupAssignee,
    ProjectGroup,
    UserGroup,
    UserGroupMember,
    Workspace,
    WorkspaceMember,
)
from plane.utils.departments import (
    DepartmentError,
    active_departments,
    adopt_department,
    adopt_department_for_members,
    clear_department,
    code_taken,
    next_sort_order,
    set_department,
)
from plane.utils.project_groups import reconcile_user, reconcile_workspace
from plane.utils.user_groups import (
    MAX_GROUP_DEPTH,
    administered_group_ids,
    can_create_group,
    can_delete_group,
    can_manage_group,
    depth_of,
    descendant_ids,
    is_workspace_admin,
    subtree_height,
    would_create_cycle,
)

from plane.utils.group_filters import allowed_group_ids

from ..base import BaseAPIView

EXTERNAL_MESSAGE = "This group is managed by the identity provider and cannot be changed here."
# What makes a group a department and how it is listed: the dictionary of departments is the workspace admins'
DEPARTMENT_FIELDS = ("kind", "code", "color", "sort_order", "is_active")
DEPARTMENT_ADMIN_MESSAGE = "Only a workspace admin can change departments."
CODE_TAKEN_MESSAGE = "Another department already has this code."


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _conflict(exc):
    """The answer to a unique constraint that a concurrent request won (between our check and our write)."""
    if "department_code" in str(exc):
        return _error(CODE_TAKEN_MESSAGE, status.HTTP_409_CONFLICT)
    return _error("A group with this name already exists here.", status.HTTP_409_CONFLICT)


class _GroupView(BaseAPIView):
    """Groups are shown to everyone who is not a guest; what a person may change is decided per group."""

    permission_classes = [WorkSpaceAdminPermission]

    def _workspace(self, slug):
        return Workspace.objects.get(slug=slug)

    def _group(self, slug, pk):
        return UserGroup.objects.filter(workspace__slug=slug, pk=pk).first()

    def _present(self, request, workspace, queryset):
        """Serialize groups with the member counts and what the requester may do with each."""
        admin = is_workspace_admin(request.user, workspace.id)
        ruled = administered_group_ids(request.user, workspace.id) if not admin else set()
        groups = list(
            queryset.annotate(member_count=Count("members", filter=Q(members__deleted_at__isnull=True), distinct=True))
        )
        for group in groups:
            group.can_manage = admin or group.id in ruled
            # A department is only ever removed by a workspace admin
            group.can_delete = admin or (
                not group.is_department and group.parent_id is not None and group.parent_id in ruled
            )
        return UserGroupSerializer(groups, many=True).data

    def _check_parent(self, workspace, group, parent_id):
        """The error for an unacceptable parent, or None. ``group`` is None when a group is being created."""
        if parent_id is None:
            return None
        parent = UserGroup.objects.filter(workspace=workspace, pk=parent_id).first()
        if parent is None:
            return "The parent group does not exist in this workspace."
        if group is not None and would_create_cycle(workspace.id, group.id, parent.id):
            return "A group cannot be moved under itself or one of its own subgroups."
        below = subtree_height(workspace.id, group.id) if group is not None else 1
        if depth_of(workspace.id, parent.id) + below > MAX_GROUP_DEPTH:
            return f"Groups can be nested at most {MAX_GROUP_DEPTH} levels deep."
        return None

    def _name_taken(self, workspace, parent_id, name, exclude_id=None):
        taken = UserGroup.objects.filter(workspace=workspace, parent_id=parent_id, name__iexact=name)
        if exclude_id:
            taken = taken.exclude(pk=exclude_id)
        return taken.exists()


class UserGroupListEndpoint(_GroupView):
    def get(self, request, slug):
        workspace = self._workspace(slug)
        queryset = UserGroup.objects.filter(workspace=workspace).order_by("name")
        kind = request.query_params.get("kind")
        if kind:
            if kind not in GroupKind.values:
                return _error("Unknown kind of group.")
            queryset = queryset.filter(kind=kind)
            if kind == GroupKind.DEPARTMENT:
                queryset = queryset.order_by("sort_order", "name")
        return Response(self._present(request, workspace, queryset), status=status.HTTP_200_OK)

    def post(self, request, slug):
        workspace = self._workspace(slug)
        serializer = UserGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = serializer.validated_data.get("parent")
        parent_id = parent.id if parent else None

        if not can_create_group(request.user, workspace.id, parent_id):
            message = (
                "Only a workspace admin can create a top-level group."
                if parent_id is None
                else "You do not manage the parent group."
            )
            return _error(message, status.HTTP_403_FORBIDDEN)
        if parent is not None and parent.is_external:
            return _error(EXTERNAL_MESSAGE)
        problem = self._check_parent(workspace, None, parent_id)
        if problem:
            return _error(problem)
        name = serializer.validated_data["name"]
        if self._name_taken(workspace, parent_id, name):
            return _error("A group with this name already exists here.", status.HTTP_409_CONFLICT)
        data = serializer.validated_data
        extra = {}
        if any(field in data for field in DEPARTMENT_FIELDS):
            if not is_workspace_admin(request.user, workspace.id):
                return _error(DEPARTMENT_ADMIN_MESSAGE, status.HTTP_403_FORBIDDEN)
            if data.get("kind") == GroupKind.DEPARTMENT:
                if code_taken(workspace.id, data.get("code", "")):
                    return _error(CODE_TAKEN_MESSAGE, status.HTTP_409_CONFLICT)
                if "sort_order" not in data:
                    extra["sort_order"] = next_sort_order(workspace.id)

        try:
            with transaction.atomic():
                group = serializer.save(workspace=workspace, **extra)
        except IntegrityError as exc:
            return _conflict(exc)
        return Response(
            self._present(request, workspace, UserGroup.objects.filter(pk=group.pk))[0],
            status=status.HTTP_201_CREATED,
        )


class UserGroupFilterableEndpoint(BaseAPIView):
    """The groups the requester may filter work items, modules, cycles and projects by (open to every workspace member).

    A workspace admin may use every group; everybody else only the groups they belong to and the ones above them.
    The full list stays with ``UserGroupListEndpoint``; this one never shows a group the person may not filter by.
    """

    permission_classes = [WorkspaceViewerPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        allowed, mine = allowed_group_ids(request.user, workspace.id)
        groups = UserGroup.objects.filter(workspace=workspace, id__in=allowed).order_by("name")
        return Response(
            [
                {
                    "id": group.id,
                    "name": group.name,
                    "source": group.source,
                    "parent_id": group.parent_id,
                    "is_member": group.id in mine,
                }
                for group in groups
            ],
            status=status.HTTP_200_OK,
        )


class UserGroupDetailEndpoint(_GroupView):
    def get(self, request, slug, pk):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return _error("Group not found.", status.HTTP_404_NOT_FOUND)
        return Response(self._present(request, workspace, UserGroup.objects.filter(pk=pk))[0])

    def patch(self, request, slug, pk):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return _error("Group not found.", status.HTTP_404_NOT_FOUND)
        admin = is_workspace_admin(request.user, workspace.id)
        if not can_manage_group(request.user, workspace.id, group.id, admin_checked=admin):
            return _error("You do not manage this group.", status.HTTP_403_FORBIDDEN)

        serializer = UserGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if group.is_external and ("name" in data or "description" in data):
            return _error(EXTERNAL_MESSAGE)
        # A mirrored group can be made a department: that says what it is here, and changes nothing of the provider's
        new_kind = data.get("kind", group.kind)
        if any(field in data and data[field] != getattr(group, field) for field in DEPARTMENT_FIELDS):
            if not admin:
                return _error(DEPARTMENT_ADMIN_MESSAGE, status.HTTP_403_FORBIDDEN)
            if new_kind == GroupKind.DEPARTMENT and code_taken(workspace.id, data.get("code", group.code), group.id):
                return _error(CODE_TAKEN_MESSAGE, status.HTTP_409_CONFLICT)
        becomes_department = new_kind == GroupKind.DEPARTMENT and not group.is_department
        stops_being_department = group.is_department and new_kind != GroupKind.DEPARTMENT

        parent_id = group.parent_id
        if "parent" in data:
            new_parent = data["parent"]
            new_parent_id = new_parent.id if new_parent else None
            if new_parent_id != group.parent_id:
                # Moving a group takes the same rights as removing it here and creating it there
                if not can_delete_group(request.user, workspace.id, group) or not can_create_group(
                    request.user, workspace.id, new_parent_id
                ):
                    return _error("You cannot move this group there.", status.HTTP_403_FORBIDDEN)
                if new_parent is not None and new_parent.is_external:
                    return _error(EXTERNAL_MESSAGE)
                problem = self._check_parent(workspace, group, new_parent_id)
                if problem:
                    return _error(problem)
                parent_id = new_parent_id

        name = data.get("name", group.name)
        if (name != group.name or parent_id != group.parent_id) and self._name_taken(
            workspace, parent_id, name, exclude_id=group.id
        ):
            return _error("A group with this name already exists here.", status.HTTP_409_CONFLICT)

        moved = parent_id != group.parent_id
        extra = {}
        if becomes_department and "sort_order" not in data:
            extra["sort_order"] = next_sort_order(workspace.id)
        try:
            with transaction.atomic():
                group = serializer.save(**extra)
                if stops_being_department:
                    clear_department(workspace.id, [group.id])
                elif becomes_department:
                    # Its members who have no department get this one, as when someone joins a department
                    adopt_department_for_members(group)
        except IntegrityError as exc:
            return _conflict(exc)
        if moved:
            # Who belongs to the groups above changed with it, and so do the projects those give
            reconcile_workspace(workspace.id)
        return Response(self._present(request, workspace, UserGroup.objects.filter(pk=pk))[0])

    def delete(self, request, slug, pk):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return _error("Group not found.", status.HTTP_404_NOT_FOUND)
        if not can_delete_group(request.user, workspace.id, group):
            return _error("You cannot delete this group.", status.HTTP_403_FORBIDDEN)
        if UserGroup.objects.filter(parent=group).exists():
            return _error("Delete or move the subgroups of this group first.")

        with transaction.atomic():
            UserGroupMember.objects.filter(group=group).delete()
            # A work item no longer points at a group that is gone
            IssueGroupAssignee.objects.filter(group=group).delete()
            # ... nor does a project have it as a member
            ProjectGroup.objects.filter(group=group).delete()
            # ... nor is it anybody's department
            clear_department(workspace.id, [group.id])
            group.delete()
        reconcile_workspace(workspace.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserGroupMembersEndpoint(_GroupView):
    def get(self, request, slug, pk):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return _error("Group not found.", status.HTTP_404_NOT_FOUND)
        nested = str(request.query_params.get("nested", "")).lower() in {"1", "true"}
        group_ids = descendant_ids(workspace.id, [group.id]) if nested else {group.id}
        members = (
            UserGroupMember.objects.filter(workspace=workspace, group_id__in=group_ids)
            .select_related("user", "group")
            .order_by("user__display_name")
        )
        return Response(UserGroupMemberSerializer(members, many=True).data)

    def post(self, request, slug, pk):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return _error("Group not found.", status.HTTP_404_NOT_FOUND)
        if not can_manage_group(request.user, workspace.id, group.id):
            return _error("You do not manage this group.", status.HTTP_403_FORBIDDEN)
        if group.is_external:
            return _error(EXTERNAL_MESSAGE)

        serializer = UserGroupMemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        if not WorkspaceMember.objects.filter(workspace=workspace, member_id=user_id, is_active=True).exists():
            return _error("Only members of the workspace can join a group.")
        if UserGroupMember.objects.filter(group=group, user_id=user_id).exists():
            return _error("This person is already in the group.", status.HTTP_409_CONFLICT)

        membership = UserGroupMember.objects.create(
            workspace=workspace, group=group, user_id=user_id, role=serializer.validated_data["role"]
        )
        adopt_department(workspace.id, user_id, group)
        reconcile_user(workspace.id, user_id)
        notify_group_membership.delay(str(group.id), str(user_id), str(request.user.id), ADDED, membership.role)
        return Response(UserGroupMemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class UserGroupMemberDetailEndpoint(_GroupView):
    def _membership(self, slug, pk, user_id):
        return (
            UserGroupMember.objects.filter(workspace__slug=slug, group_id=pk, user_id=user_id)
            .select_related("user", "group")
            .first()
        )

    def _check(self, request, slug, pk, user_id):
        workspace = self._workspace(slug)
        group = self._group(slug, pk)
        if group is None:
            return None, None, _error("Group not found.", status.HTTP_404_NOT_FOUND)
        if not can_manage_group(request.user, workspace.id, group.id):
            return None, None, _error("You do not manage this group.", status.HTTP_403_FORBIDDEN)
        if group.is_external:
            return None, None, _error(EXTERNAL_MESSAGE)
        membership = self._membership(slug, pk, user_id)
        if membership is None:
            return None, None, _error("This person is not in the group.", status.HTTP_404_NOT_FOUND)
        return group, membership, None

    def patch(self, request, slug, pk, user_id):
        _, membership, error = self._check(request, slug, pk, user_id)
        if error:
            return error
        serializer = UserGroupMemberWriteSerializer(data={"user_id": user_id, **request.data})
        serializer.is_valid(raise_exception=True)
        previous_role = membership.role
        membership.role = serializer.validated_data["role"]
        update_fields = ["role", "updated_at"]
        if membership.role != previous_role and membership.via_department:
            # Changed by hand: the membership is no longer only what the department assignment made
            membership.via_department = False
            update_fields.append("via_department")
        membership.save(update_fields=update_fields)
        if membership.role != previous_role:
            notify_group_membership.delay(
                str(membership.group_id), str(user_id), str(request.user.id), ROLE_CHANGED, membership.role
            )
        return Response(UserGroupMemberSerializer(membership).data)

    def delete(self, request, slug, pk, user_id):
        _, membership, error = self._check(request, slug, pk, user_id)
        if error:
            return error
        with transaction.atomic():
            membership.delete()
            clear_department(membership.workspace_id, [membership.group_id], user_id=membership.user_id)
        reconcile_user(membership.workspace_id, membership.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DepartmentListEndpoint(BaseAPIView):
    """The departments that are switched on, for pickers and the notice to people without one (any member)."""

    permission_classes = [WorkspaceViewerPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        return Response(DepartmentLiteSerializer(active_departments(workspace.id), many=True).data)


class WorkspaceMemberDepartmentEndpoint(BaseAPIView):
    """
    The department of a workspace member, set by a workspace admin only (their own included).

    Members and guests do not choose their department: belonging to a department's group can make a person a member
    of the projects the group is a member of, so choosing it would let anyone into those projects.
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def patch(self, request, slug, pk):
        workspace = Workspace.objects.get(slug=slug)
        member = (
            WorkspaceMember.objects.filter(workspace=workspace, pk=pk, is_active=True, member__is_bot=False)
            .select_related("department")
            .first()
        )
        if member is None:
            return _error("Workspace member not found.", status.HTTP_404_NOT_FOUND)

        serializer = WorkspaceMemberDepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department_id = serializer.validated_data["department"]
        department = None
        if department_id is not None:
            department = UserGroup.objects.filter(workspace=workspace, pk=department_id).first()
            if department is None:
                return _error("The department does not exist in this workspace.")
        try:
            set_department(member, department)
        except DepartmentError as exc:
            return _error(str(exc))
        return Response({"id": member.id, "department": member.department_id}, status=status.HTTP_200_OK)
