# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Baselines of a project: the planning dates of its work items as they were when somebody saved the plan."""

# Django imports
from django.db import models

# Module imports
from .project import ProjectBaseModel

# Saving one more is refused; an old baseline has to be deleted first.
MAX_BASELINES_PER_PROJECT = 20
MAX_BASELINE_NAME_LENGTH = 255
MAX_BASELINE_DESCRIPTION_LENGTH = 2000


class ProjectBaseline(ProjectBaseModel):
    """A saved plan of a project. ``created_by`` is who saved it; at most one live baseline of a project is active."""

    name = models.CharField(max_length=MAX_BASELINE_NAME_LENGTH)
    description = models.TextField(blank=True, default="", max_length=MAX_BASELINE_DESCRIPTION_LENGTH)
    is_active = models.BooleanField(default=False)
    # how many work items were captured; kept here so that listing baselines does not count rows
    item_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Project Baseline"
        verbose_name_plural = "Project Baselines"
        db_table = "project_baselines"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(is_active=True, deleted_at__isnull=True),
                name="project_baseline_one_active_per_project",
            )
        ]

    def __str__(self):
        return f"{self.name} <{self.project_id}>"


class BaselineItem(ProjectBaseModel):
    """The dates and the state group of one work item at the moment the baseline was saved."""

    baseline = models.ForeignKey(ProjectBaseline, on_delete=models.CASCADE, related_name="items")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="baseline_items")
    start_date = models.DateField(null=True, blank=True)
    # the end of the bar on the timeline
    finish_date = models.DateField(null=True, blank=True)
    # the due date (a deadline)
    target_date = models.DateField(null=True, blank=True)
    state_group = models.CharField(max_length=20, blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Baseline Item"
        verbose_name_plural = "Baseline Items"
        db_table = "project_baseline_items"
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["baseline", "issue"],
                condition=models.Q(deleted_at__isnull=True),
                name="baseline_item_unique_baseline_issue_when_deleted_at_null",
            )
        ]

    def __str__(self):
        return f"{self.baseline_id} {self.issue_id}"
