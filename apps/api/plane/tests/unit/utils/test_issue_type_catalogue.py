# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The catalogue of work item types: what each entry brings, and that adding it never makes a second type."""

from io import StringIO

import pytest
from django.core.management import call_command

from plane.app.serializers import IssueTypeSerializer
from plane.db.models import IssueType, IssueTypeKind, IssueTypeProperty, Project
from plane.utils.content_validator import validate_html_content
from plane.utils.issue_type_catalogue import (
    CATALOGUE,
    CATALOGUE_KEYS,
    CREATED,
    EXISTS,
    UPDATED,
    add_catalogue_types,
    catalogue_language,
    list_catalogue,
)
from plane.utils.issue_type_property import clean_property_list
from plane.utils.project_issue_types import ensure_project_kind_type


@pytest.mark.unit
class TestCatalogueContent:
    def test_the_entries(self):
        assert CATALOGUE_KEYS == ("task", "bug", "story", "change_request", "milestone")
        kinds = {entry["key"]: entry["kind"] for entry in CATALOGUE}
        assert kinds["milestone"] == IssueTypeKind.MILESTONE
        assert {kinds[key] for key in ("task", "bug", "story", "change_request")} == {IssueTypeKind.STANDARD}

    @pytest.mark.parametrize("entry", CATALOGUE, ids=lambda entry: entry["key"])
    def test_every_icon_passes_the_logo_validation(self, entry):
        assert IssueTypeSerializer().validate_logo_props(entry["logo_props"]) == entry["logo_props"]

    @pytest.mark.parametrize("entry", CATALOGUE, ids=lambda entry: entry["key"])
    @pytest.mark.parametrize("language", ["en", "pl"])
    def test_every_template_survives_the_sanitiser_and_every_property_is_valid(self, entry, language):
        text = entry["text"][language]
        is_valid, _error, sanitized = validate_html_content(text["template"])
        assert is_valid and sanitized == text["template"]
        assert len(clean_property_list(text["properties"])) == len(text["properties"])

    def test_suggested_properties(self):
        titles = {entry["key"]: [prop["title"] for prop in entry["text"]["en"]["properties"]] for entry in CATALOGUE}
        assert titles["bug"] == ["Severity", "Environment", "Steps to reproduce"]
        assert titles["change_request"] == ["Reason", "Impact"]

    @pytest.mark.parametrize(
        "language, expected", [("pl", "pl"), ("pl-PL", "pl"), ("en", "en"), ("de", "en"), (None, "en"), ("", "en")]
    )
    def test_language(self, language, expected):
        assert catalogue_language(language) == expected


@pytest.mark.unit
class TestAddCatalogueTypes:
    @pytest.mark.django_db
    def test_adds_every_entry_once(self, workspace, create_user):
        results = add_catalogue_types(workspace.id, created_by_id=create_user.id)
        assert [(key, status) for key, _type, status in results] == [(key, CREATED) for key in CATALOGUE_KEYS]
        bug = IssueType.objects.get(workspace=workspace, name="Bug")
        assert bug.kind == IssueTypeKind.STANDARD
        assert bug.logo_props["icon"]["name"] == "bug_report"
        assert bug.description_template.startswith("<h3>")
        assert list(IssueTypeProperty.objects.filter(issue_type=bug).values_list("title", "property_type")) == [
            ("Severity", "dropdown"),
            ("Environment", "text"),
            ("Steps to reproduce", "text"),
        ]

        again = add_catalogue_types(workspace.id, created_by_id=create_user.id)
        assert {status for _key, _type, status in again} == {EXISTS}
        assert IssueType.objects.filter(workspace=workspace).count() == len(CATALOGUE_KEYS)
        assert IssueTypeProperty.objects.filter(issue_type=bug).count() == 3

    @pytest.mark.django_db
    def test_task_becomes_the_default_only_when_there_is_none(self, workspace):
        add_catalogue_types(workspace.id, ["task"])
        assert IssueType.objects.get(workspace=workspace, name="Task").is_default is True

    @pytest.mark.django_db
    def test_task_does_not_take_the_default_from_another_type(self, workspace):
        IssueType.objects.create(workspace=workspace, name="General", is_default=True)
        add_catalogue_types(workspace.id, ["task"])
        assert IssueType.objects.get(workspace=workspace, name="Task").is_default is False

    @pytest.mark.django_db
    def test_a_type_with_the_name_in_another_language_counts_as_the_entry(self, workspace):
        bug = IssueType.objects.create(workspace=workspace, name="bug")
        [(key, issue_type, status)] = add_catalogue_types(workspace.id, ["bug"], language="pl")
        assert (key, issue_type.id, status) == ("bug", bug.id, EXISTS)
        assert not IssueType.objects.filter(workspace=workspace, name="Błąd").exists()
        assert list_catalogue(workspace.id, "pl")[1]["existing_type_id"] == str(bug.id)

    @pytest.mark.django_db
    def test_polish(self, workspace):
        add_catalogue_types(workspace.id, ["bug", "milestone"], language="pl")
        bug = IssueType.objects.get(workspace=workspace, name="Błąd")
        assert "Waga" in bug.properties.values_list("title", flat=True)
        assert IssueType.objects.get(workspace=workspace, kind=IssueTypeKind.MILESTONE).name == "Kamień milowy"

    @pytest.mark.django_db
    def test_unknown_keys_are_refused(self, workspace):
        with pytest.raises(ValueError):
            add_catalogue_types(workspace.id, ["task", "nope"])
        assert not IssueType.objects.filter(workspace=workspace).exists()


@pytest.mark.unit
class TestMilestoneEntryIsTheSystemType:
    @pytest.fixture
    def project(self, workspace, create_user):
        return Project.objects.create(
            name="Plan", identifier="PL", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
        )

    @pytest.mark.django_db
    def test_the_catalogue_milestone_is_the_one_the_system_links(self, workspace, project):
        [(_key, milestone, status)] = add_catalogue_types(workspace.id, ["milestone"])
        assert status == CREATED
        assert milestone.kind == IssueTypeKind.MILESTONE
        assert ensure_project_kind_type(project, IssueTypeKind.MILESTONE).id == milestone.id
        assert IssueType.objects.filter(workspace=workspace, kind=IssueTypeKind.MILESTONE).count() == 1

    @pytest.mark.django_db
    def test_an_existing_milestone_type_is_adopted_not_doubled(self, workspace, project):
        system = ensure_project_kind_type(project, IssueTypeKind.MILESTONE)
        assert not system.logo_props and not system.description_template
        [(_key, milestone, status)] = add_catalogue_types(workspace.id, ["milestone"])
        assert (milestone.id, status) == (system.id, UPDATED)
        system.refresh_from_db()
        assert system.logo_props["icon"]["name"] == "diamond"
        assert system.description_template
        assert IssueType.objects.filter(workspace=workspace, kind=IssueTypeKind.MILESTONE).count() == 1
        # nothing left to fill in
        assert add_catalogue_types(workspace.id, ["milestone"])[0][2] == EXISTS

    @pytest.mark.django_db
    def test_what_an_admin_set_on_the_milestone_type_is_kept(self, workspace):
        logo = {"in_use": "emoji", "emoji": {"value": "128681"}}
        own = IssueType.objects.create(
            workspace=workspace,
            name="Gate",
            kind=IssueTypeKind.MILESTONE,
            logo_props=logo,
            description_template="<p>Ours</p>",
        )
        add_catalogue_types(workspace.id, ["milestone"])
        own.refresh_from_db()
        assert (own.name, own.logo_props, own.description_template) == ("Gate", logo, "<p>Ours</p>")

    @pytest.mark.django_db
    def test_a_standard_type_named_milestone_does_not_stop_the_entry(self, workspace):
        IssueType.objects.create(workspace=workspace, name="Milestone")
        [(_key, milestone, status)] = add_catalogue_types(workspace.id, ["milestone"])
        assert status == CREATED
        assert milestone.kind == IssueTypeKind.MILESTONE
        assert milestone.name == "Milestone work item"


@pytest.mark.unit
class TestSeedCommand:
    @pytest.mark.django_db
    def test_seeds_a_workspace(self, workspace):
        out = StringIO()
        call_command("seed_work_item_type_catalogue", workspace.slug, "--keys", "bug", "story", stdout=out)
        assert set(IssueType.objects.filter(workspace=workspace).values_list("name", flat=True)) == {"Bug", "Story"}
        assert "bug: created (Bug)" in out.getvalue()
