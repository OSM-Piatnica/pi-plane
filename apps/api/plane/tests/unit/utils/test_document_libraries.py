# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Folder paths of document libraries and where a project's new documents go (no database)."""

from types import SimpleNamespace

import pytest

from plane.db.models.document import DocumentLibrary, DocumentProvider, ProjectDocumentSettings, ProjectDocumentStore
from plane.utils.document_store import libraries
from plane.utils.document_store.libraries import (
    FolderPathError,
    ProjectTarget,
    folder_web_url,
    normalize_folder_path,
    project_target,
)

pytestmark = pytest.mark.unit

LIBRARY_URL = "https://contoso.sharepoint.com/sites/Projects/Shared%20Documents"


class TestNormalizeFolderPath:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (None, ""),
            ("", ""),
            ("  /  ", ""),
            ("Pi-Plane", "Pi-Plane"),
            ("/Pi-Plane/Docs/", "Pi-Plane/Docs"),
            ("Pi-Plane//Docs", "Pi-Plane/Docs"),
            ("Pi-Plane\\Docs", "Pi-Plane/Docs"),
            (" Klienci / Opakowania 2027 ", "Klienci/Opakowania 2027"),
            ("Zażółć/gęślą", "Zażółć/gęślą"),
        ],
    )
    def test_accepts_and_tidies(self, value, expected):
        assert normalize_folder_path(value) == expected

    @pytest.mark.parametrize(
        "value", ["a/../b", "a/./b", "Docs:2027", "Q?", "a*b", "50%", "#1", "ends with a dot.", "~$lock", "con"]
    )
    def test_refuses_names_sharepoint_would_change(self, value):
        with pytest.raises(FolderPathError):
            normalize_folder_path(value)

    def test_refuses_too_deep_and_too_long(self):
        with pytest.raises(FolderPathError):
            normalize_folder_path("/".join(["a"] * 21))
        with pytest.raises(FolderPathError):
            normalize_folder_path("/".join(["x" * 100] * 5))
        assert normalize_folder_path("/".join(["a"] * 20)).count("/") == 19


class TestFolderWebUrl:
    def test_appends_encoded_parts(self):
        assert folder_web_url(LIBRARY_URL, ("Pi-Plane", "PACK 1")) == f"{LIBRARY_URL}/Pi-Plane/PACK%201"
        assert folder_web_url(LIBRARY_URL + "/", ()) == LIBRARY_URL
        assert folder_web_url(LIBRARY_URL, ("Zażółć",)) == f"{LIBRARY_URL}/Za%C5%BC%C3%B3%C5%82%C4%87"

    def test_nothing_without_a_library_address(self):
        assert folder_web_url("", ("a",)) == ""


class TestProjectTarget:
    def _project(self):
        return SimpleNamespace(identifier="PACK", workspace_id="w")

    def _library(self, root_path="Pi-Plane/Docs"):
        return DocumentLibrary(drive_id="b!x", root_path=root_path, provider=DocumentProvider.SHAREPOINT)

    def test_item_folder_follows_the_plan(self):
        target = ProjectTarget(DocumentProvider.SHAREPOINT, self._library(), ("PACK",))
        assert target.item_folder("PACK", 12) == ("PACK", "PACK-12")
        assert target.item_folder("PACK", None) == ("PACK",)
        assert target.folder == ("Pi-Plane", "Docs", "PACK")

    def test_workspace_default_with_the_project_identifier(self, monkeypatch):
        library = self._library()
        monkeypatch.setattr(libraries, "default_library", lambda workspace_id: library)
        target = project_target(self._project(), sharepoint_enabled=True, settings=None)
        assert target.provider == DocumentProvider.SHAREPOINT
        assert target.library is library
        assert target.project_folder == ("PACK",)

    def test_custom_folder_replaces_the_identifier(self, monkeypatch):
        library = self._library()
        monkeypatch.setattr(libraries, "default_library", lambda workspace_id: library)
        settings = ProjectDocumentSettings(store=ProjectDocumentStore.WORKSPACE, folder="Klienci/ACME")
        target = project_target(self._project(), sharepoint_enabled=True, settings=settings)
        assert target.folder == ("Pi-Plane", "Docs", "Klienci", "ACME")
        assert target.item_folder("PACK", 3) == ("Klienci", "ACME", "PACK-3")

    def test_a_chosen_library_wins_over_the_default(self, monkeypatch):
        default, chosen = self._library(), self._library(root_path="")
        monkeypatch.setattr(libraries, "default_library", lambda workspace_id: default)
        settings = ProjectDocumentSettings(store=ProjectDocumentStore.SHAREPOINT, library=chosen)
        target = project_target(self._project(), sharepoint_enabled=True, settings=settings)
        assert target.library is chosen
        assert target.folder == ("PACK",)

    def test_native_when_chosen_without_library_or_without_sharepoint(self, monkeypatch):
        monkeypatch.setattr(libraries, "default_library", lambda workspace_id: self._library())
        chosen = ProjectDocumentSettings(store=ProjectDocumentStore.NATIVE)
        assert project_target(self._project(), sharepoint_enabled=True, settings=chosen).native_reason == "chosen"
        off = project_target(self._project(), sharepoint_enabled=False, settings=None)
        assert (off.provider, off.library, off.native_reason) == (DocumentProvider.NATIVE, None, "sharepoint_off")
        monkeypatch.setattr(libraries, "default_library", lambda workspace_id: None)
        none = project_target(self._project(), sharepoint_enabled=True, settings=None)
        assert none.native_reason == "no_library"
