# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import models
from django.db.models import Q

from .base import BaseModel
from .project import ProjectBaseModel


class RaciRole(models.TextChoices):
    """
    What a department is to a work item. The names are neutral: the letters people see (R / A / C / I in English,
    O / Z / K / I in Polish) belong to the interface.
    """

    RESPONSIBLE = "responsible", "Responsible"
    APPROVER = "approver", "Approver"
    CONSULTED = "consulted", "Consulted"
    INFORMED = "informed", "Informed"


class IssueRaci(ProjectBaseModel):
    """
    The role of a department (a user group of kind "department") on a work item.

    A department has one role per work item; several departments may share a role, "responsible" included.
    """

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="issue_raci")
    group = models.ForeignKey("db.UserGroup", on_delete=models.CASCADE, related_name="issue_raci")
    role = models.CharField(max_length=20, choices=RaciRole.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "group"],
                condition=Q(deleted_at__isnull=True),
                name="issue_raci_unique_issue_group_when_deleted_at_null",
            )
        ]
        indexes = [models.Index(fields=["group", "role"], name="issue_raci_group_role_idx")]
        verbose_name = "Issue RACI"
        verbose_name_plural = "Issue RACI"
        db_table = "issue_raci"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.issue_id} {self.group_id} {self.role}"


class RaciNotificationSetting(BaseModel):
    """
    Which roles hear about which events on a work item, for one workspace (``plane.utils.raci_notifications``).

    ``matrix`` is ``{event: [role, ...]}``. An event it does not name keeps its default, and a workspace without a
    row has the defaults of SPEC-02 throughout.
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="raci_notification_settings")
    matrix = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(deleted_at__isnull=True),
                name="raci_notification_setting_unique_workspace_when_deleted_at_null",
            )
        ]
        verbose_name = "RACI Notification Setting"
        verbose_name_plural = "RACI Notification Settings"
        db_table = "raci_notification_settings"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace_id}"
