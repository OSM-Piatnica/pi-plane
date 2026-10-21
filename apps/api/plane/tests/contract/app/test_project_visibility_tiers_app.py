# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The three project visibility tiers (``Project.network``):

* Secret (0): invisible to everyone who is not a member (workspace admins still list it),
* Private (1): listed for workspace members but locked: people request access or are invited,
* Public (2): listed for workspace members, who can join it at once.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Project, ProjectAccessRequest, ProjectMember, User, WorkspaceMember

SECRET, PRIVATE, PUBLIC = 0, 1, 2
ADMIN, MEMBER, GUEST = 20, 15, 5


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _user(workspace, role, label):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(email=f"{label}-{unique_id}@plane.so", username=f"{label}_{unique_id}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _project(workspace, network, identifier, members=()):
    project = Project.objects.create(
        name=f"{identifier} project", identifier=identifier, workspace=workspace, network=network
    )
    for user, role in members:
        ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=role)
    return project


@pytest.fixture
def owner(create_user):
    """A workspace admin (the workspace fixture's owner)."""
    return create_user


@pytest.fixture
def insider(db, workspace):
    """A workspace member who belongs to every project below."""
    return _user(workspace, MEMBER, "insider")


@pytest.fixture
def outsider(db, workspace):
    """A workspace member who belongs to none of them."""
    return _user(workspace, MEMBER, "outsider")


@pytest.fixture
def guest(db, workspace):
    return _user(workspace, GUEST, "guest")


@pytest.fixture
def projects(db, workspace, insider):
    return {
        "secret": _project(workspace, SECRET, "SEC", [(insider, ADMIN)]),
        "private": _project(workspace, PRIVATE, "PRV", [(insider, ADMIN)]),
        "public": _project(workspace, PUBLIC, "PUB", [(insider, ADMIN)]),
    }


def _listed_names(client, workspace):
    response = client.get(f"/api/workspaces/{workspace.slug}/projects/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    return {project["identifier"] for project in (data["results"] if isinstance(data, dict) else data)}


@pytest.mark.contract
@pytest.mark.django_db
class TestGalleryVisibility:
    def test_member_of_the_projects_sees_all_three(self, workspace, projects, insider):
        assert _listed_names(_client(insider), workspace) == {"SEC", "PRV", "PUB"}

    def test_other_workspace_members_see_private_and_public_but_not_secret(self, workspace, projects, outsider):
        assert _listed_names(_client(outsider), workspace) == {"PRV", "PUB"}

    def test_guests_see_only_their_own_projects(self, workspace, projects, guest):
        assert _listed_names(_client(guest), workspace) == set()

    def test_workspace_admins_keep_seeing_every_project(self, workspace, projects, owner):
        assert _listed_names(_client(owner), workspace) == {"SEC", "PRV", "PUB"}


@pytest.mark.contract
@pytest.mark.django_db
class TestOpeningAProject:
    def _get(self, user, workspace, project):
        return _client(user).get(f"/api/workspaces/{workspace.slug}/projects/{project.id}/")

    def test_member_opens_all_three(self, workspace, projects, insider):
        for project in projects.values():
            assert self._get(insider, workspace, project).status_code == status.HTTP_200_OK

    def test_non_member_is_refused_a_secret_project_without_details(self, workspace, projects, outsider):
        response = self._get(outsider, workspace, projects["secret"])
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "network" not in response.json()

    def test_non_member_is_told_a_private_project_is_locked(self, workspace, projects, outsider):
        response = self._get(outsider, workspace, projects["private"])
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["network"] == PRIVATE

    def test_non_member_can_join_a_public_project(self, workspace, projects, outsider):
        assert self._get(outsider, workspace, projects["public"]).status_code == status.HTTP_409_CONFLICT


@pytest.mark.contract
@pytest.mark.django_db
class TestJoiningDirectly:
    def _join(self, user, workspace, project):
        return _client(user).post(
            f"/api/users/me/workspaces/{workspace.slug}/projects/invitations/",
            {"project_ids": [str(project.id)]},
            format="json",
        )

    def test_members_join_public_projects(self, workspace, projects, outsider):
        assert self._join(outsider, workspace, projects["public"]).status_code == status.HTTP_201_CREATED
        assert ProjectMember.objects.filter(project=projects["public"], member=outsider, is_active=True).exists()

    @pytest.mark.parametrize("tier", ["private", "secret"])
    def test_members_cannot_join_private_or_secret_projects(self, workspace, projects, outsider, tier):
        assert self._join(outsider, workspace, projects[tier]).status_code == status.HTTP_403_FORBIDDEN
        assert not ProjectMember.objects.filter(project=projects[tier], member=outsider).exists()

    def test_workspace_admins_can_join_a_private_project(self, workspace, projects, owner):
        assert self._join(owner, workspace, projects["private"]).status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestAccessRequests:
    def _url(self, workspace, project, suffix=""):
        return f"/api/workspaces/{workspace.slug}/projects/{project.id}/access-requests/{suffix}"

    def _request_access(self, user, workspace, project, message=None):
        data = {"message": message} if message is not None else {}
        return _client(user).post(self._url(workspace, project), data, format="json")

    def test_a_member_requests_access_to_a_private_project_once(self, workspace, projects, outsider):
        first = self._request_access(outsider, workspace, projects["private"], "Please let me in")
        assert first.status_code == status.HTTP_201_CREATED
        assert first.json()["status"] == "pending"
        assert first.json()["message"] == "Please let me in"

        again = self._request_access(outsider, workspace, projects["private"])
        assert again.status_code == status.HTTP_200_OK
        assert again.json()["id"] == first.json()["id"]
        assert ProjectAccessRequest.objects.filter(project=projects["private"], requester=outsider).count() == 1

    def test_requests_are_only_for_private_projects(self, workspace, projects, outsider):
        assert self._request_access(outsider, workspace, projects["public"]).status_code == status.HTTP_400_BAD_REQUEST
        # a secret project is not revealed
        assert self._request_access(outsider, workspace, projects["secret"]).status_code == status.HTTP_404_NOT_FOUND

    def test_members_of_the_project_and_guests_cannot_request(self, workspace, projects, insider, guest):
        assert self._request_access(insider, workspace, projects["private"]).status_code == status.HTTP_409_CONFLICT
        assert self._request_access(guest, workspace, projects["private"]).status_code == status.HTTP_403_FORBIDDEN

    def test_a_long_message_is_refused(self, workspace, projects, outsider):
        response = self._request_access(outsider, workspace, projects["private"], "x" * 501)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_only_project_admins_list_and_decide(self, workspace, projects, insider, outsider):
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)
        other = _user(workspace, MEMBER, "bystander")

        assert _client(other).get(self._url(workspace, projects["private"])).status_code == status.HTTP_403_FORBIDDEN
        assert (
            _client(outsider)
            .patch(
                self._url(workspace, projects["private"], f"{access_request.id}/"),
                {"status": "approved"},
                format="json",
            )
            .status_code
            == status.HTTP_403_FORBIDDEN
        )

        listed = _client(insider).get(self._url(workspace, projects["private"]))
        assert listed.status_code == status.HTTP_200_OK
        assert [row["id"] for row in listed.json()] == [str(access_request.id)]
        assert listed.json()[0]["requester_detail"]["id"] == str(outsider.id)

    def test_the_requester_sees_the_state_of_their_request(self, workspace, projects, outsider):
        mine = _client(outsider).get(self._url(workspace, projects["private"], "me/"))
        assert mine.status_code == status.HTTP_200_OK
        assert mine.json() == {"status": None}

        self._request_access(outsider, workspace, projects["private"])
        assert _client(outsider).get(self._url(workspace, projects["private"], "me/")).json()["status"] == "pending"

    def test_approving_adds_the_requester_with_their_workspace_role(self, workspace, projects, insider, outsider):
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)

        response = _client(insider).patch(
            self._url(workspace, projects["private"], f"{access_request.id}/"), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "approved"
        membership = ProjectMember.objects.get(project=projects["private"], member=outsider)
        assert membership.is_active is True
        assert membership.role == MEMBER
        access_request.refresh_from_db()
        assert access_request.decided_by_id == insider.id and access_request.decided_at is not None
        # the project now opens for them
        opened = _client(outsider).get(f"/api/workspaces/{workspace.slug}/projects/{projects['private'].id}/")
        assert opened.status_code == status.HTTP_200_OK

    def test_approving_reactivates_a_former_member_at_the_workspace_role(self, workspace, projects, insider, outsider):
        former = ProjectMember.objects.create(
            workspace=workspace, project=projects["private"], member=outsider, role=ADMIN, is_active=False
        )
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)

        response = _client(insider).patch(
            self._url(workspace, projects["private"], f"{access_request.id}/"), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        former.refresh_from_db()
        assert former.is_active is True and former.role == MEMBER

    def test_rejecting_adds_nobody_and_allows_a_new_request(self, workspace, projects, insider, outsider):
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)

        response = _client(insider).patch(
            self._url(workspace, projects["private"], f"{access_request.id}/"), {"status": "rejected"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert not ProjectMember.objects.filter(project=projects["private"], member=outsider).exists()
        assert self._request_access(outsider, workspace, projects["private"]).status_code == status.HTTP_201_CREATED

    def test_a_decided_request_cannot_be_decided_again(self, workspace, projects, insider, outsider):
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)
        url = self._url(workspace, projects["private"], f"{access_request.id}/")
        assert _client(insider).patch(url, {"status": "rejected"}, format="json").status_code == status.HTTP_200_OK
        assert (
            _client(insider).patch(url, {"status": "approved"}, format="json").status_code == status.HTTP_409_CONFLICT
        )

    def test_a_decision_must_be_approved_or_rejected(self, workspace, projects, insider, outsider):
        access_request = ProjectAccessRequest.objects.create(project=projects["private"], requester=outsider)
        url = self._url(workspace, projects["private"], f"{access_request.id}/")
        assert (
            _client(insider).patch(url, {"status": "pending"}, format="json").status_code == status.HTTP_400_BAD_REQUEST
        )

    def test_a_request_to_another_project_cannot_be_decided_through_this_one(
        self, workspace, projects, insider, outsider
    ):
        other = _project(workspace, PRIVATE, "OTH", [(insider, ADMIN)])
        access_request = ProjectAccessRequest.objects.create(project=other, requester=outsider)
        url = self._url(workspace, projects["private"], f"{access_request.id}/")
        assert (
            _client(insider).patch(url, {"status": "approved"}, format="json").status_code == status.HTTP_404_NOT_FOUND
        )
        assert not ProjectMember.objects.filter(project=other, member=outsider).exists()
