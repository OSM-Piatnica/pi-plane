# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Names of states and priorities in every language of the Plane UI, as Copilot gets them."""

from unittest import mock

import pytest

import plane_labels
import sync_service


@pytest.fixture(autouse=True)
def shipped_labels_only(tmp_path, monkeypatch):
    """Only the translations shipped with the connector (no plane_labels.json read from an instance)."""
    monkeypatch.delenv("PLANE_LABEL_LANGUAGES", raising=False)
    with mock.patch.object(plane_labels, "LABELS_FILE", tmp_path / "plane_labels.json"):
        plane_labels._cache.update({"mtime": None, "data": None})
        yield


def test_every_plane_language_is_shipped():
    assert len(plane_labels.all_languages()) >= 25
    assert {"W trakcie", "In corso", "In Bearbeitung", "En cours", "В процессе"} <= plane_labels.all_state_names(
        "In Progress")
    assert {"Wysoki", "Alta", "Hoch", "Haute"} <= plane_labels.all_priority_names("high")
    # a custom state name is the same in every language
    assert plane_labels.all_state_names("Testy QA") == {"Testy QA"}


def test_copilot_gets_every_language_by_default(monkeypatch):
    langs = plane_labels.languages()
    assert langs[:2] == ["pl", "en"] and len(langs) >= 25
    labels = plane_labels.state_labels("In Progress")
    assert labels["pl"] == "W trakcie" and labels["it"] == "In corso" and labels["de"] == "In Bearbeitung"
    assert plane_labels.priority_labels("medium")["pl"] == "Średni"

    monkeypatch.setenv("PLANE_LABEL_LANGUAGES", "pl,en")
    assert plane_labels.languages() == ["pl", "en"]
    assert set(plane_labels.state_labels("Done")) == {"pl", "en"}


def test_one_line_groups_the_languages_with_the_same_name():
    line = plane_labels.bilingual("In Progress", plane_labels.state_labels("In Progress"))
    assert line.startswith("In Progress (pl,pl-x-podlaski: W trakcie; ")
    assert "it: In corso" in line and "de: In Bearbeitung" in line
    assert "en: In Progress" not in line  # the same as the name itself
    assert plane_labels.bilingual("Testy QA", plane_labels.state_labels("Testy QA")) == "Testy QA"


def test_a_language_the_instance_cannot_give_comes_from_the_shipped_file():
    stored = {"languages": {"de": {"states": {}, "priority": {"high": "High"}}}}
    with mock.patch.object(plane_labels, "_load", lambda: stored):
        assert "Hoch" in plane_labels.all_priority_names("high")


def test_the_work_item_sent_to_copilot_names_state_and_priority_in_every_language():
    ext = sync_service._map_work_item_to_external_item(
        {"id": "p1", "name": "Scan box", "identifier": "SB"},
        {"id": "i1", "name": "Montaz", "sequence_id": 3, "state": {"name": "In Progress"}, "priority": "high",
         "assignees": [], "description_html": "<p>Opis</p>", "created_at": "2026-01-01T00:00:00Z"},
        [{"type": "user", "value": "oid-a"}])
    content = ext["content"]["value"]
    assert "Status: In Progress (pl,pl-x-podlaski: W trakcie;" in content
    assert "it: In corso" in content and "fr: En cours" in content
    assert "Priorytet: high (" in content and "de: Hoch" in content and "pl,pl-x-podlaski: Wysoki" in content
