# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Exporting the members of a project: formats, rows, who may, and the file read back by the members import."""

import csv
import json
from io import BytesIO, StringIO
from unittest import mock

import pytest
from openpyxl import load_workbook
from rest_framework.test import APIClient

from plane.db.models import (
    Project,
    ProjectGroup,
    ProjectMember,
    User,
    UserGroup,
    UserGroupMember,
    WorkspaceMember,
)
from plane.utils.porters.formatters import CSVFormatter
from plane.utils.project_groups import reconcile_project

ADMIN, MEMBER, GUEST = 20, 15, 5
SLUG = "test-workspace"
HEADERS = ["Email", "Group", "Role", "Name", "Source", "Via Group", "Raised By Group", "Joined"]


@pytest.fixture(autouse=True)
def _no_background_work(db):
    with (
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
        mock.patch("plane.app.views.project.member_import.project_add_user_email"),
    ):
        yield


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Export", identifier="PEX", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    return project


def _person(workspace, email, role=MEMBER, display_name=""):
    user = User.objects.create(email=email, username=email, first_name=email.split("@")[0], display_name=display_name)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _group(workspace, name, parent=None):
    return UserGroup.objects.create(workspace=workspace, name=name, parent=parent)


def _url(project, slug=SLUG):
    return f"/api/workspaces/{slug}/projects/{project.id}/members/export/"


def _rows(response):
    return list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))


@pytest.fixture
def populated(workspace, project, create_user):
    """An admin, a direct member, a guest raised by a group, a person only in through a group, groups and noise."""
    ada = _person(workspace, "ada@example.com", display_name="Ada")
    ProjectMember.objects.create(project=project, member=ada, role=MEMBER, is_active=True)
    carol = _person(workspace, "carol@example.com", display_name="Carol")
    ProjectMember.objects.create(project=project, member=carol, role=GUEST, is_active=True)
    bob = _person(workspace, "bob@example.com", display_name="Bob")
    gone = _person(workspace, "gone@example.com")
    ProjectMember.objects.create(project=project, member=gone, role=MEMBER, is_active=False)
    bot = User.objects.create(email="bot@example.com", username="bot", is_bot=True)
    WorkspaceMember.objects.create(workspace=workspace, member=bot, role=MEMBER)
    ProjectMember.objects.create(project=project, member=bot, role=MEMBER, is_active=True)

    sales = _group(workspace, "Sales")
    poland = _group(workspace, "Poland", parent=sales)
    UserGroupMember.objects.create(workspace=workspace, group=poland, user=bob)
    UserGroupMember.objects.create(workspace=workspace, group=sales, user=carol)
    ProjectGroup.objects.create(project=project, workspace=workspace, group=sales, role=MEMBER)
    ProjectGroup.objects.create(project=project, workspace=workspace, group=poland, role=GUEST)
    reconcile_project(project.id)

    other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
    stranger = _person(workspace, "stranger@example.com")
    ProjectMember.objects.create(project=other, member=stranger, role=ADMIN, is_active=True)
    ProjectGroup.objects.create(project=other, workspace=workspace, group=_group(workspace, "Elsewhere"), role=GUEST)
    return {"ada": ada, "bob": bob, "carol": carol}


@pytest.mark.contract
@pytest.mark.django_db
class TestExportRows:
    def test_csv_has_groups_first_then_direct_people_by_email(self, session_client, project, populated, create_user):
        response = session_client.get(_url(project), {"format": "csv"})

        assert response.status_code == 200, getattr(response, "data", None)
        assert response["Content-Type"].startswith("text/csv")
        assert response["Content-Disposition"].startswith('attachment; filename="PEX-members-')
        assert response["Content-Disposition"].endswith('.csv"')
        rows = _rows(response)
        assert list(rows[0].keys()) == HEADERS
        assert [(r["Source"], r["Email"], r["Group"], r["Role"]) for r in rows] == [
            ("group", "", "Sales", "15"),
            ("group", "", "Sales / Poland", "5"),
            ("person", "ada@example.com", "", "15"),
            ("person", "carol@example.com", "", "5"),
            ("person", create_user.email, "", "20"),
        ]
        emails = [r["Email"] for r in rows if r["Source"] == "person"]
        assert emails == sorted(emails)
        assert "bob@example.com" not in emails  # only in through a group
        assert "gone@example.com" not in emails and "bot@example.com" not in emails
        assert "stranger@example.com" not in emails
        assert all(r["Group"] != "Elsewhere" for r in rows)

    def test_a_person_raised_by_a_group_is_written_with_their_own_role(self, session_client, project, populated):
        rows = {r["Email"]: r for r in _rows(session_client.get(_url(project), {"format": "csv"})) if r["Email"]}

        assert rows["carol@example.com"]["Role"] == "5"
        assert rows["carol@example.com"]["Raised By Group"] == "yes"
        assert rows["ada@example.com"]["Raised By Group"] == ""
        assert rows["ada@example.com"]["Name"] == "Ada"
        assert len(rows["ada@example.com"]["Joined"]) == 10

    def test_people_through_a_group_are_added_on_request(self, session_client, project, populated):
        rows = _rows(session_client.get(_url(project), {"format": "csv", "include_via_group": "1"}))

        bob = next(r for r in rows if r["Email"] == "bob@example.com")
        assert bob["Source"] == "person (via group)"
        # He is in Poland, which is below Sales, so both links give him the project (the better role counts)
        assert bob["Role"] == "15"
        assert bob["Via Group"] == "Sales; Sales / Poland"

    def test_xlsx(self, session_client, project, populated):
        response = session_client.get(_url(project), {"format": "xlsx"})

        assert response.status_code == 200
        assert response["Content-Disposition"].endswith('.xlsx"')
        sheet = load_workbook(BytesIO(response.content)).active
        values = list(sheet.values)
        assert list(values[0]) == HEADERS
        assert ("Sales", 15) in [(row[1], row[2]) for row in values[1:]]

    def test_json(self, session_client, project, populated):
        response = session_client.get(_url(project), {"format": "json"})

        assert response.status_code == 200
        assert response["Content-Disposition"].endswith('.json"')
        data = json.loads(response.content)
        assert data[0]["group"] == "Sales" and data[0]["role"] == 15 and data[0]["source"] == "group"
        assert {row["email"] for row in data if row["email"]} >= {"ada@example.com", "carol@example.com"}

    def test_semicolon_delimiter(self, session_client, project, populated):
        text = session_client.get(_url(project), {"format": "csv", "delimiter": ";"}).content.decode("utf-8-sig")

        assert text.splitlines()[0].startswith("Email;Group;Role;")

    def test_unknown_format_is_a_bad_request(self, session_client, project):
        assert session_client.get(_url(project), {"format": "pdf"}).status_code == 400

    def test_formula_in_a_name_is_neutralised_in_spreadsheets_only(self, session_client, workspace, project):
        evil = _person(workspace, "evil@example.com", display_name="=1+1")
        ProjectMember.objects.create(project=project, member=evil, role=MEMBER, is_active=True)

        csv_rows = _rows(session_client.get(_url(project), {"format": "csv"}))
        assert next(r for r in csv_rows if r["Email"] == "evil@example.com")["Name"] == "'=1+1"
        data = json.loads(session_client.get(_url(project), {"format": "json"}).content)
        assert next(r for r in data if r["email"] == "evil@example.com")["name"] == "=1+1"


@pytest.mark.contract
@pytest.mark.django_db
class TestWhoMayExport:
    def test_only_project_admins_may_export(self, workspace, project):
        member = _person(workspace, "member@example.com")
        ProjectMember.objects.create(project=project, member=member, role=MEMBER, is_active=True)

        assert _client(member).get(_url(project), {"format": "csv"}).status_code == 403

    def test_someone_outside_the_project_may_not_export(self, workspace, project):
        outsider = _person(workspace, "outsider@example.com", role=ADMIN)

        assert _client(outsider).get(_url(project), {"format": "csv"}).status_code in (403, 404)


@pytest.mark.contract
@pytest.mark.django_db
class TestRoundTrip:
    def test_an_exported_file_imported_into_a_fresh_project_gives_the_same_members(
        self, session_client, workspace, project, populated, create_user
    ):
        text = session_client.get(_url(project), {"format": "csv", "include_via_group": "1"}).content.decode(
            "utf-8-sig"
        )
        rows = [
            {
                "row": index + 2,
                "email": row.get("email"),
                "group": row.get("group"),
                "role": row.get("role"),
                "source": row.get("source"),
            }
            for index, row in enumerate(CSVFormatter().decode(text))
        ]
        fresh = Project.objects.create(name="Fresh", identifier="FRS", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=fresh, member=create_user, role=ADMIN, is_active=True)

        response = session_client.post(
            f"/api/workspaces/{SLUG}/projects/{fresh.id}/members/import/", {"rows": rows}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["skipped"] == []
        assert set(ProjectGroup.objects.filter(project=fresh).values_list("group_id", "role")) == set(
            ProjectGroup.objects.filter(project=project).values_list("group_id", "role")
        )
        direct = lambda p: {  # noqa: E731
            (m.member_id, m.direct_role if m.direct_role is not None else m.role)
            for m in ProjectMember.objects.filter(project=p, is_active=True, via_group=False, member__is_bot=False)
        }
        assert direct(fresh) == direct(project)
        # bob came in through his group, not as a direct member
        assert ProjectMember.objects.get(project=fresh, member=populated["bob"]).via_group
