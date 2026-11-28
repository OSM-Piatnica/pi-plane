# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import models
from django.db.models import Q

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
