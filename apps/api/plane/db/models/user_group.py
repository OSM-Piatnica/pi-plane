# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_init, post_save
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
    # Any other OpenID Connect provider, through the claim of its ID token that lists the groups
    OIDC = "oidc", "Single sign-on"


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


class ProjectGroupRole(models.IntegerChoices):
    """What a group may be in a project: never an Admin, project admins stay named people."""

    MEMBER = 15, "Member"
    GUEST = 5, "Guest"


class ProjectGroup(ProjectBaseModel):
    """A group as a member of a project: whoever belongs to the group (and the groups below it) is a member."""

    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name="project_links")
    role = models.PositiveSmallIntegerField(choices=ProjectGroupRole.choices, default=ProjectGroupRole.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "group"],
                condition=Q(deleted_at__isnull=True),
                name="project_group_unique_project_group_when_deleted_at_null",
            )
        ]
        verbose_name = "Project Group"
        verbose_name_plural = "Project Groups"
        db_table = "project_groups"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        if self.role not in ProjectGroupRole.values:
            raise ValidationError({"role": "A group can only be a Member or a Guest of a project."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project_id} {self.group_id}"


@receiver(post_init, sender="db.WorkspaceMember")
def remember_workspace_member_state(sender, instance, **kwargs):
    """Remember the role and the active flag a workspace member was loaded with, to see whether they change."""
    state = instance.__dict__
    instance._project_group_state = (state.get("role"), state.get("is_active"))


@receiver(post_save, sender="db.WorkspaceMember")
def mirror_stored_groups_on_join(sender, instance, created, **kwargs):
    """A person who joins a workspace gets the groups their identity provider reported at their last sign-in.

    What groups give in projects follows the person's workspace role and whether they are in the workspace at all, so
    it is worked out again when they join, change role or are deactivated or reactivated.
    """
    from plane.utils.project_groups import reconcile_user

    if created and instance.is_active:
        from plane.utils.user_group_sync import sync_workspace_from_stored

        sync_workspace_from_stored(instance.member, instance.workspace_id)
    before = getattr(instance, "_project_group_state", None)
    changed = created or before is None or before != (instance.role, instance.is_active)
    instance._project_group_state = (instance.role, instance.is_active)
    if changed and instance.member_id:
        reconcile_user(instance.workspace_id, instance.member_id)
