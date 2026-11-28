# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The document endpoints against the native store: uploading in two steps, versions, downloads, the checksum check
and who may see what. Pi-Plane's own object storage is played by an in-memory fake.
"""

import hashlib
from unittest import mock

import pytest
from rest_framework.test import APIClient

from plane.bgtasks.document_checksum_task import check_version
from plane.db.models import (
    ChecksumStatus,
    Document,
    DocumentVersion,
    Issue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.tests.document_storage_fake import FakeObjectStorage

ADMIN, MEMBER, GUEST = 20, 15, 5
PDF = b"%PDF-1.7 artwork v1"
PDF2 = b"%PDF-1.7 artwork v2, corrected"


def sha(content):
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def storage():
    return FakeObjectStorage()


@pytest.fixture(autouse=True)
def _fakes(db, storage):
    with (
        mock.patch("plane.settings.storage.get_storage", return_value=storage),
        mock.patch("plane.bgtasks.document_checksum_task.verify_document_version_checksum.delay") as delay,
        mock.patch("plane.db.mixins.soft_delete_related_objects.delay"),
    ):
        yield delay


@pytest.fixture
def checksum_delay(_fakes):
    return _fakes


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(name="Packaging", identifier="PACK", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=ADMIN, is_active=True)
    State.objects.create(
        name="Todo", group="unstarted", color="#fff", project=project, workspace=workspace, default=True
    )
    return project


def _issue(project, name="Label", created_by=None):
    issue = Issue.objects.create(
        name=name, project=project, workspace=project.workspace, state=State.objects.get(project=project)
    )
    if created_by is not None:
        Issue.objects.filter(pk=issue.pk).update(created_by=created_by)
        issue.refresh_from_db()
    return issue


@pytest.fixture
def issue(project):
    return _issue(project)


def _person(workspace, project, email, role):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, workspace=workspace, is_active=True)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _base(project):
    return f"/api/workspaces/{project.workspace.slug}/projects/{project.id}/documents/"


def _begin(client, project, **body):
    body.setdefault("type", "application/pdf")
    return client.post(f"{_base(project)}uploads/", body, format="json")


def _finish(client, project, token, content):
    return client.post(
        f"{_base(project)}uploads/finish/", {"upload_token": token, "sha256": sha(content)}, format="json"
    )


def _upload(client, project, storage, content=PDF, **body):
    """Begin, send the bytes as the browser would, finish; the answer of finish."""
    body.setdefault("size", len(content))
    begun = _begin(client, project, **body)
    assert begun.status_code == 200, begun.data
    storage.put(begun.data["upload"]["fields"]["key"], content)
    return _finish(client, project, begun.data["upload_token"], content)


@pytest.mark.contract
class TestUpload:
    def test_begin_gives_a_presigned_post_and_records_nothing_yet(self, session_client, project, issue, storage):
        response = _begin(session_client, project, name="Label front.pdf", size=len(PDF), issue_id=str(issue.id))
        assert response.status_code == 200, response.data
        assert response.data["provider"] == "native"
        upload = response.data["upload"]
        assert upload["kind"] == "presigned_post"
        assert upload["fields"]["key"].startswith(f"{project.workspace_id}/documents/")
        assert response.data["upload_token"]
        assert Document.objects.count() == 0

    def test_finishing_records_the_document_and_version_one(
        self, session_client, create_user, project, issue, storage, checksum_delay, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = _upload(session_client, project, storage, name="Label front.pdf", issue_id=str(issue.id))
        assert response.status_code == 200, response.data
        document = Document.objects.get()
        assert document.issue_id == issue.id
        assert document.provider == "native"
        assert document.name == "Label front.pdf"
        version = DocumentVersion.objects.get()
        assert (version.number, version.size, version.sha256) == (1, len(PDF), sha(PDF))
        assert version.checksum_status == ChecksumStatus.PENDING
        assert version.uploaded_by_id == create_user.id
        assert response.data["version"]["number"] == 1
        assert "storage_key" not in response.data["version"]
        checksum_delay.assert_called_once_with(str(version.id))

    def test_finishing_the_same_upload_twice_gives_the_same_version(self, session_client, project, storage):
        begun = _begin(session_client, project, name="a.pdf", size=len(PDF))
        storage.put(begun.data["upload"]["fields"]["key"], PDF)
        first = _finish(session_client, project, begun.data["upload_token"], PDF)
        second = _finish(session_client, project, begun.data["upload_token"], PDF)
        assert first.data["version"]["id"] == second.data["version"]["id"]
        assert DocumentVersion.objects.count() == 1

    def test_finishing_before_the_bytes_arrived_is_refused(self, session_client, project):
        begun = _begin(session_client, project, name="a.pdf", size=len(PDF))
        response = _finish(session_client, project, begun.data["upload_token"], PDF)
        assert response.status_code == 400
        assert response.data["error_code"] == "upload_incomplete"
        assert Document.objects.count() == 0

    def test_a_missing_or_malformed_checksum_is_refused(self, session_client, project, storage):
        begun = _begin(session_client, project, name="a.pdf", size=len(PDF))
        storage.put(begun.data["upload"]["fields"]["key"], PDF)
        response = session_client.post(
            f"{_base(project)}uploads/finish/",
            {"upload_token": begun.data["upload_token"], "sha256": "abc"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_sha256"

    def test_a_tampered_token_is_refused(self, session_client, project):
        response = _finish(session_client, project, "not-a-token", PDF)
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_upload_token"

    def test_another_persons_upload_cannot_be_finished(self, session_client, workspace, project, storage):
        begun = _begin(session_client, project, name="a.pdf", size=len(PDF))
        storage.put(begun.data["upload"]["fields"]["key"], PDF)
        other = _person(workspace, project, "other@example.com", MEMBER)
        response = _finish(_client(other), project, begun.data["upload_token"], PDF)
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_upload_token"

    def test_a_type_that_is_not_allowed_is_refused(self, session_client, project):
        response = _begin(session_client, project, name="x.exe", size=3, type="application/x-msdownload")
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_type"

    def test_a_file_over_the_limit_is_refused(self, session_client, project):
        response = _begin(session_client, project, name="big.pdf", size=10**12)
        assert response.status_code == 400
        assert response.data["error_code"] == "file_too_large"

    def test_a_work_item_of_another_project_is_not_found(self, session_client, workspace, project, create_user):
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
        State.objects.create(name="Todo", group="unstarted", color="#fff", project=other, workspace=workspace)
        foreign = _issue(other)
        response = _begin(session_client, project, name="a.pdf", size=3, issue_id=str(foreign.id))
        assert response.status_code == 404


@pytest.mark.contract
class TestVersions:
    def test_a_new_version_gets_the_next_number_and_the_document_keeps_its_name(self, session_client, project, storage):
        first = _upload(session_client, project, storage, name="Label.pdf")
        document_id = first.data["id"]
        second = _upload(session_client, project, storage, content=PDF2, document_id=document_id)
        assert second.status_code == 200, second.data
        assert second.data["id"] == document_id
        assert second.data["version"]["number"] == 2
        assert second.data["name"] == "Label.pdf"
        listed = session_client.get(f"{_base(project)}{document_id}/versions/")
        assert [version["number"] for version in listed.data] == [2, 1]
        one = session_client.get(f"{_base(project)}{document_id}/versions/1/")
        assert one.data["sha256"] == sha(PDF)
        assert session_client.get(f"{_base(project)}{document_id}/versions/3/").status_code == 404

    def test_a_new_version_must_be_the_same_type(self, session_client, project, storage):
        first = _upload(session_client, project, storage, name="Label.pdf")
        response = _begin(session_client, project, document_id=first.data["id"], size=3, type="image/png")
        assert response.status_code == 400
        assert response.data["error_code"] == "type_changed"

    def test_versions_are_never_renumbered(self, session_client, project, storage):
        first = _upload(session_client, project, storage, name="Label.pdf")
        _upload(session_client, project, storage, content=PDF2, document_id=first.data["id"])
        DocumentVersion.objects.get(number=2).delete()
        third = _upload(session_client, project, storage, content=b"third", document_id=first.data["id"])
        assert third.data["version"]["number"] == 3


@pytest.mark.contract
class TestReading:
    def test_the_list_and_the_detail(self, session_client, project, issue, storage):
        on_item = _upload(session_client, project, storage, name="Label.pdf", issue_id=str(issue.id))
        _upload(session_client, project, storage, name="Brief.pdf")
        listed = session_client.get(_base(project))
        assert listed.status_code == 200
        assert {document["name"] for document in listed.data} == {"Label.pdf", "Brief.pdf"}
        of_item = session_client.get(_base(project), {"issue_id": str(issue.id)})
        assert [document["name"] for document in of_item.data] == ["Label.pdf"]
        assert of_item.data[0]["latest_version"]["number"] == 1
        assert of_item.data[0]["version_count"] == 1
        detail = session_client.get(f"{_base(project)}{on_item.data['id']}/")
        assert detail.status_code == 200
        assert [version["number"] for version in detail.data["versions"]] == [1]
        assert detail.data["changed_externally"] is False

    def test_download_redirects_to_the_object_of_that_version(self, session_client, project, storage):
        document = _upload(session_client, project, storage, name="Label.pdf")
        response = session_client.get(f"{_base(project)}{document.data['id']}/versions/1/download/")
        assert response.status_code == 302
        key = DocumentVersion.objects.get().storage_key
        assert response["Location"].startswith(f"https://s3.example.test/uploads/{key}")
        assert "disposition=attachment" in response["Location"]

    def test_a_mismatching_version_is_not_served_silently(self, session_client, project, storage):
        document = _upload(session_client, project, storage, name="Label.pdf")
        DocumentVersion.objects.update(checksum_status=ChecksumStatus.MISMATCH)
        url = f"{_base(project)}{document.data['id']}/versions/1/download/"
        refused = session_client.get(url)
        assert refused.status_code == 409
        assert refused.data["error_code"] == "checksum_mismatch"
        assert session_client.get(url, {"accept_mismatch": "true"}).status_code == 302

    def test_the_native_store_has_no_thumbnail_and_nothing_to_adopt(self, session_client, project, storage):
        document = _upload(session_client, project, storage, name="Label.pdf")
        thumbnail = session_client.get(f"{_base(project)}{document.data['id']}/thumbnail/")
        assert thumbnail.status_code == 404
        assert thumbnail.data["error_code"] == "no_thumbnail"
        adopt = session_client.post(f"{_base(project)}{document.data['id']}/adopt/")
        assert adopt.status_code == 409
        assert adopt.data["error_code"] == "nothing_to_adopt"

    def test_a_document_of_another_project_is_not_found(self, session_client, create_user, workspace, project, storage):
        document = _upload(session_client, project, storage, name="Label.pdf")
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace)
        ProjectMember.objects.create(project=other, member=create_user, role=ADMIN, is_active=True)
        response = session_client.get(f"{_base(other)}{document.data['id']}/")
        assert response.status_code == 404


@pytest.mark.contract
class TestChecksum:
    def _version(self, session_client, project, storage):
        _upload(session_client, project, storage, name="Label.pdf")
        return DocumentVersion.objects.select_related("document").get()

    def test_matching_bytes_are_verified(self, session_client, project, storage):
        version = self._version(session_client, project, storage)
        assert check_version(version) == ChecksumStatus.VERIFIED
        version.refresh_from_db()
        assert version.checksum_status == ChecksumStatus.VERIFIED
        assert version.checksum_checked_at is not None

    def test_bytes_changed_in_the_storage_are_a_mismatch(self, session_client, project, storage):
        version = self._version(session_client, project, storage)
        storage.put(version.storage_key, b"%PDF-1.7 tampered!!")
        assert check_version(version) == ChecksumStatus.MISMATCH
        version.refresh_from_db()
        assert version.checksum_status == ChecksumStatus.MISMATCH
        # The reference value is kept: the mismatch stays visible
        assert version.sha256 == sha(PDF)


@pytest.mark.contract
class TestPermissions:
    def test_a_restricted_guest_sees_project_documents_and_those_of_own_work_items(
        self, session_client, create_user, workspace, project, storage
    ):
        guest = _person(workspace, project, "guest@example.com", GUEST)
        own = _issue(project, "Own", created_by=guest)
        foreign = _issue(project, "Foreign", created_by=create_user)
        _upload(session_client, project, storage, name="Project.pdf")
        _upload(session_client, project, storage, name="Own.pdf", issue_id=str(own.id))
        hidden = _upload(session_client, project, storage, name="Foreign.pdf", issue_id=str(foreign.id))

        client = _client(guest)
        listed = client.get(_base(project))
        assert listed.status_code == 200
        assert {document["name"] for document in listed.data} == {"Project.pdf", "Own.pdf"}
        assert client.get(f"{_base(project)}{hidden.data['id']}/").status_code == 403
        assert client.get(f"{_base(project)}{hidden.data['id']}/versions/1/download/").status_code == 403

    def test_a_guest_of_a_project_where_guests_see_everything_sees_all(
        self, session_client, create_user, workspace, project, storage
    ):
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        guest = _person(workspace, project, "guest@example.com", GUEST)
        foreign = _issue(project, "Foreign", created_by=create_user)
        _upload(session_client, project, storage, name="Foreign.pdf", issue_id=str(foreign.id))
        assert len(_client(guest).get(_base(project)).data) == 1

    def test_guests_do_not_upload(self, workspace, project):
        guest = _person(workspace, project, "guest@example.com", GUEST)
        response = _begin(_client(guest), project, name="a.pdf", size=3)
        assert response.status_code == 403

    def test_a_member_uploads(self, workspace, project, storage):
        member = _person(workspace, project, "member@example.com", MEMBER)
        response = _upload(_client(member), project, storage, name="a.pdf")
        assert response.status_code == 200

    def test_someone_outside_the_project_sees_nothing(self, workspace, project, storage, session_client):
        document = _upload(session_client, project, storage, name="a.pdf")
        outsider = User.objects.create(email="out@example.com", username="out@example.com")
        WorkspaceMember.objects.create(workspace=workspace, member=outsider, role=MEMBER)
        client = _client(outsider)
        assert client.get(_base(project)).status_code == 403
        assert client.get(f"{_base(project)}{document.data['id']}/").status_code == 403
