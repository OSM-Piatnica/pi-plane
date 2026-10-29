# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .base import BaseModel
from .project import ProjectBaseModel


class GroupRole(models.IntegerChoices):
    """A role inside one group (and the groups nested below it), not a workspace role."""

    ADMIN = 20, "Group admin"
    MEMBER = 15, "Member"


class GroupSource(models.TextChoices):
    """Where a group comes from: made here, or mirrored from the identity provider a person signed in with."""

    LOCAL = "local", "Local"
    ENTRA = "entra", "Microsoft Entra"
    GOOGLE = "google", "Google"


class UserGroup(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="user_groups")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey("db.UserGroup", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    source = models.CharField(max_length=20, choices=GroupSource.choices, default=GroupSource.LOCAL)
    # The identity provider's own id for a group managed outside; empty for local groups
    external_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "parent", "name"],
                condition=Q(deleted_at__isnull=True, parent__isnull=False),
                name="user_group_unique_name_in_parent_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=Q(deleted_at__isnull=True, parent__isnull=True),
                name="user_group_unique_top_level_name_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "source", "external_id"],
                condition=Q(deleted_at__isnull=True, external_id__isnull=False),
                name="user_group_unique_external_id_when_deleted_at_null",
            ),
        ]
        verbose_name = "User Group"
        verbose_name_plural = "User Groups"
        db_table = "user_groups"
        ordering = ("name",)

    @property
    def is_external(self):
        return self.source != GroupSource.LOCAL

    def __str__(self):
        return f"{self.name} <{self.workspace_id}>"


class UserGroupMember(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="user_group_members")
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_group_memberships")
    role = models.PositiveSmallIntegerField(choices=GroupRole.choices, default=GroupRole.MEMBER)
    # Rows written by the sign-in sync are replaced by it; the ones made by hand are never touched by it
    managed_externally = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=Q(deleted_at__isnull=True),
                name="user_group_member_unique_group_user_when_deleted_at_null",
            )
        ]
        verbose_name = "User Group Member"
        verbose_name_plural = "User Group Members"
        db_table = "user_group_members"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.group_id} {self.user_id}"


class IssueGroupAssignee(ProjectBaseModel):
    """A work item assigned to a whole group: whoever belongs to the group (and the groups below it) is on it."""

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="issue_group_assignee")
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name="issue_assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "group"],
                condition=Q(deleted_at__isnull=True),
                name="issue_group_assignee_unique_issue_group_when_deleted_at_null",
            )
        ]
        verbose_name = "Issue Group Assignee"
        verbose_name_plural = "Issue Group Assignees"
        db_table = "issue_group_assignees"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.issue_id} {self.group_id}"


@receiver(post_save, sender="db.WorkspaceMember")
def mirror_stored_groups_on_join(sender, instance, created, **kwargs):
    """A person who joins a workspace gets the groups their identity provider reported at their last sign-in."""
    if not created or not instance.is_active:
        return
    from plane.utils.user_group_sync import sync_workspace_from_stored

    sync_workspace_from_stored(instance.member, instance.workspace_id)
