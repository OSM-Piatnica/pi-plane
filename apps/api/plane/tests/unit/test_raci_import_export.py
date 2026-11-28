# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RACI in work item files: the RACI column and "O:XX" labels on import, and the column on export (D4)."""

from itertools import count

import pytest
from django.db.models import Prefetch

from plane.db.models import (
    GroupKind,
    Issue,
    IssueLabel,
    IssueRaci,
    Label,
    Module,
    ModuleIssue,
    Project,
    ProjectMember,
    State,
    User,
    UserGroup,
    WorkspaceFeature,
    WorkspaceMember,
)
from plane.utils.community_work_item_import import import_community_work_items_into_project
from plane.utils.porters.exporter import DataExporter
from plane.utils.porters.importer import DataImporter
from plane.utils.porters.serializers.issue import IssueExportSerializer
from plane.utils.project_work_item_import import WorkItemImportOptions

ADMIN, MEMBER = 20, 15
_SEQUENCE = count(1)


def _project(workspace, user, name, identifier, raci=True):
    project = Project.objects.create(
        name=name, identifier=identifier, workspace=workspace, created_by=user, is_raci_enabled=raci
    )
    ProjectMember.objects.create(project=project, member=user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", color="#3B82F6", project=project, workspace=workspace, group="unstarted", default=True
    )
    return project


@pytest.fixture
def raci_on(workspace):
    WorkspaceFeature.objects.create(workspace=workspace, key="raci", is_enabled=True)


@pytest.fixture
def departments(workspace):
    def department(name, code, sort_order, **extra):
        return UserGroup.objects.create(
            workspace=workspace, name=name, code=code, kind=GroupKind.DEPARTMENT, sort_order=sort_order, **extra
        )

    return {
        "rm": department("Marketing", "RM", 1, color="#3f76ff"),
        "za": department("Zarząd", "ZA", 2),
        "pr": department("Produkcja", "PR", 3),
        "old": department("Archiwum", "AR", 4, is_active=False),
    }


def _import(project, user, rows, options=None):
    warnings = []
    import_community_work_items_into_project(project=project, user=user, rows=rows, warnings=warnings, options=options)
    return warnings


def _roles(project, name):
    issue = Issue.objects.get(project=project, name=name)
    return dict(IssueRaci.objects.filter(issue=issue).values_list("group__code", "role"))


def _labels(project, name):
    issue = Issue.objects.get(project=project, name=name)
    return set(IssueLabel.objects.filter(issue=issue).values_list("label__name", flat=True))


def _row(name, **extra):
    return {"identifier": f"DEMO-{next(_SEQUENCE)}", "name": name, "state_name": "Todo", **extra}


@pytest.mark.unit
@pytest.mark.django_db
class TestImportingRaci:
    def test_the_column_takes_polish_and_english_letters(self, workspace, create_user, raci_on, departments):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(
            project,
            create_user,
            [_row("Polskie", raci="O:RM;Z:ZA;K:PR"), _row("Angielskie", raci="R:RM;A:ZA;C:PR")],
        )

        expected = {"RM": "responsible", "ZA": "approver", "PR": "consulted"}
        assert _roles(project, "Polskie") == expected
        assert _roles(project, "Angielskie") == expected
        assert not [warning for warning in warnings if "RACI" in warning]

    def test_a_department_is_found_by_name_too_and_two_may_be_responsible(
        self, workspace, create_user, raci_on, departments
    ):
        project = _project(workspace, create_user, "Demo", "DEMO")

        _import(project, create_user, [_row("Dwa", raci="O:marketing;O:PR")])

        assert _roles(project, "Dwa") == {"RM": "responsible", "PR": "responsible"}

    def test_prototype_labels_become_roles_and_other_labels_stay(self, workspace, create_user, raci_on, departments):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(project, create_user, [_row("Etykiety", labels='["O:RM", "Z:ZA", "pilne", "O:XX"]')])

        assert _roles(project, "Etykiety") == {"RM": "responsible", "ZA": "approver"}
        # "O:XX" names no department, so it is kept as a label rather than lost
        assert _labels(project, "Etykiety") == {"pilne", "O:XX"}
        assert not Label.objects.filter(project=project, name__in=["O:RM", "Z:ZA"]).exists()
        assert not [warning for warning in warnings if "RACI" in warning]

    def test_the_column_comes_first_and_a_department_keeps_one_role(self, workspace, create_user, raci_on, departments):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(project, create_user, [_row("Oba", raci="O:RM", labels='["K:RM", "I:PR"]')])

        assert _roles(project, "Oba") == {"RM": "responsible", "PR": "informed"}
        assert any('department "RM" already has a role' in warning for warning in warnings)

    def test_unknown_unreadable_and_switched_off_departments_are_reported(
        self, workspace, create_user, raci_on, departments
    ):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(project, create_user, [_row("Błędy", raci="O:RM;K:XX;Q:PR;I:AR")])

        assert _roles(project, "Błędy") == {"RM": "responsible"}
        assert any('unknown RACI department "XX"' in warning for warning in warnings)
        assert any('RACI entry "Q:PR"' in warning for warning in warnings)
        assert any('department "AR" is switched off' in warning for warning in warnings)

    def test_nothing_comes_in_while_the_project_has_raci_off(self, workspace, create_user, raci_on, departments):
        project = _project(workspace, create_user, "Demo", "DEMO", raci=False)

        warnings = _import(project, create_user, [_row("Wyłączone", raci="O:RM", labels='["O:RM"]')])

        assert _roles(project, "Wyłączone") == {}
        assert _labels(project, "Wyłączone") == {"O:RM"}
        assert any("RACI is not switched on for this project" in warning for warning in warnings)

    def test_nothing_comes_in_while_the_workspace_has_raci_off(self, workspace, create_user, departments):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(project, create_user, [_row("Wyłączone", raci="O:RM")])

        assert _roles(project, "Wyłączone") == {}
        assert any("RACI is not switched on for this project" in warning for warning in warnings)

    def test_a_member_who_may_not_set_roles_imports_the_work_items_without_them(
        self, workspace, create_user, raci_on, departments
    ):
        project = _project(workspace, create_user, "Demo", "DEMO")
        member = User.objects.create(email="member@example.com", username="member")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=MEMBER)
        ProjectMember.objects.create(project=project, member=member, role=MEMBER, is_active=True)

        warnings = _import(project, member, [_row("Członek", raci="O:RM")])

        assert _roles(project, "Członek") == {}
        assert any("only a project admin or the project lead" in warning for warning in warnings)

    def test_the_option_leaves_the_roles_out(self, workspace, create_user, raci_on, departments):
        project = _project(workspace, create_user, "Demo", "DEMO")

        warnings = _import(
            project, create_user, [_row("Bez RACI", raci="O:RM")], options=WorkItemImportOptions(raci=False)
        )

        assert _roles(project, "Bez RACI") == {}
        assert any("RACI data that this import was asked to leave out" in warning for warning in warnings)


def _export(project, file_format, letters):
    queryset = (
        Issue.objects.filter(project=project)
        .select_related("project", "project__workspace", "state", "created_by")
        .prefetch_related(
            "issue_module__module", Prefetch("issue_raci", queryset=IssueRaci.objects.select_related("group"))
        )
    )
    exporter = DataExporter(IssueExportSerializer, format_type=file_format, context={"raci_letters": letters})
    _, content = exporter.export("export", queryset)
    return content.encode("utf-8") if isinstance(content, str) else content


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize("file_format", ["csv", "xlsx", "json"])
@pytest.mark.parametrize("letters", ["pl", "en"])
def test_an_exported_work_item_keeps_its_roles_and_modules_when_imported_again(
    file_format, letters, workspace, create_user, raci_on, departments
):
    source = _project(workspace, create_user, "Źródło", "SRC")
    module = Module.objects.create(name="Etap 1", project=source, workspace=workspace)
    issue = Issue.objects.create(
        name="Projekt etykiety", project=source, workspace=workspace, state=State.objects.get(project=source)
    )
    ModuleIssue.objects.create(module=module, issue=issue, project=source, workspace=workspace)
    for key, role in (("rm", "responsible"), ("pr", "responsible"), ("za", "approver"), ("old", "informed")):
        IssueRaci.objects.create(issue=issue, group=departments[key], role=role, project=source, workspace=workspace)

    content = _export(source, file_format, letters)

    target = _project(workspace, create_user, "Cel", "TGT")
    warnings = _import(target, create_user, DataImporter(format_type=file_format).decode(content))

    imported = Issue.objects.get(project=target, name="Projekt etykiety")
    assert ModuleIssue.objects.filter(issue=imported, module__name="Etap 1").exists()
    # a switched-off department keeps its role where it is, but a new work item cannot be given one
    assert _roles(target, "Projekt etykiety") == {"RM": "responsible", "PR": "responsible", "ZA": "approver"}
    assert any('department "AR" is switched off' in warning for warning in warnings)


@pytest.mark.unit
@pytest.mark.django_db
def test_an_export_writes_the_letters_of_the_language(workspace, create_user, raci_on, departments):
    project = _project(workspace, create_user, "Demo", "DEMO")
    issue = Issue.objects.create(
        name="Litery", project=project, workspace=workspace, state=State.objects.get(project=project)
    )
    for key, role in (("za", "approver"), ("rm", "responsible"), ("pr", "consulted")):
        IssueRaci.objects.create(issue=issue, group=departments[key], role=role, project=project, workspace=workspace)

    polish = DataImporter(format_type="json").decode(_export(project, "json", "pl"))
    english = DataImporter(format_type="json").decode(_export(project, "json", "en"))

    assert polish[0]["raci"] == "O:RM;Z:ZA;K:PR"
    assert english[0]["raci"] == "R:RM;A:ZA;C:PR"


@pytest.mark.unit
@pytest.mark.django_db
def test_an_export_leaves_the_column_empty_where_raci_is_off(workspace, create_user, departments):
    project = _project(workspace, create_user, "Demo", "DEMO")
    issue = Issue.objects.create(
        name="Wyłączone", project=project, workspace=workspace, state=State.objects.get(project=project)
    )
    IssueRaci.objects.create(
        issue=issue, group=departments["rm"], role="responsible", project=project, workspace=workspace
    )

    rows = DataImporter(format_type="json").decode(_export(project, "json", "pl"))

    assert rows[0]["raci"] == ""
