# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, datetime, timezone

import pytest

from plane.db.models import Cycle, CycleIssue, Issue, Module, ModuleIssue, Project, ProjectMember, State
from plane.utils.community_work_item_import import import_community_work_items_into_project
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.importer import DataImporter
from plane.utils.porters.serializers.issue import IssueExportSerializer


def _project(workspace, user, name, identifier, tz="UTC"):
    project = Project.objects.create(
        name=name, identifier=identifier, workspace=workspace, created_by=user, timezone=tz
    )
    ProjectMember.objects.create(project=project, member=user, role=20, is_active=True)
    State.objects.create(
        name="Todo",
        color="#3B82F6",
        project=project,
        workspace=workspace,
        group="unstarted",
        sequence=10000,
        default=True,
        created_by=user,
    )
    return project


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize("file_format", ["csv", "xlsx", "json"])
def test_exported_work_item_keeps_module_cycle_and_dates_when_imported_again(file_format, workspace, create_user):
    source = _project(workspace, create_user, "Source", "SRC", tz="Europe/Warsaw")
    module = Module.objects.create(name="Kampania", project=source, workspace=workspace)
    # A cycle form stores the first day at the project's midnight and the last day at 23:59, in UTC
    cycle = Cycle.objects.create(
        name="Sprint 1",
        project=source,
        workspace=workspace,
        owned_by=create_user,
        start_date=datetime(2026, 5, 31, 22, 0, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 14, 21, 59, tzinfo=timezone.utc),
    )
    issue = Issue.objects.create(
        name="Round trip",
        project=source,
        workspace=workspace,
        state=State.objects.get(project=source),
        start_date=date(2026, 6, 2),
        target_date=date(2026, 6, 9),
        created_by=create_user,
    )
    ModuleIssue.objects.create(module=module, issue=issue, project=source, workspace=workspace)
    CycleIssue.objects.create(cycle=cycle, issue=issue, project=source, workspace=workspace)

    queryset = (
        Issue.objects.filter(project=source)
        .select_related("project", "state", "created_by")
        .prefetch_related("issue_cycle__cycle", "issue_module__module")
    )
    _, content = DataExporter(IssueExportSerializer, format_type=file_format).export("export", queryset)
    if isinstance(content, str):
        content = content.encode("utf-8")

    target = _project(workspace, create_user, "Target", "TGT", tz="Europe/Warsaw")
    import_community_work_items_into_project(
        project=target,
        user=create_user,
        rows=DataImporter(format_type=file_format).decode(content),
        warnings=[],
    )

    imported = Issue.objects.get(project=target, name="Round trip")
    assert ModuleIssue.objects.filter(issue=imported, module__name="Kampania").exists()
    assert imported.start_date == date(2026, 6, 2)
    assert imported.target_date == date(2026, 6, 9)
    new_cycle = CycleIssue.objects.get(issue=imported).cycle
    assert new_cycle.name == "Sprint 1"
    assert new_cycle.start_date == cycle.start_date
    assert new_cycle.end_date == cycle.end_date
