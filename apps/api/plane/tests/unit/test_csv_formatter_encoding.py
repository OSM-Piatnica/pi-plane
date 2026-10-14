# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.utils.porters.importer import DataImporter
from plane.utils.porters.formatters import CSVFormatter, UTF8_SIG_BOM


class TestCSVFormatterEncoding:
    def test_encode_includes_utf8_bom_for_excel(self):
        csv_content = CSVFormatter(delimiter=";").encode(
            [{"name": "Marketing produktów", "identifier": "AGRO"}]
        )
        assert csv_content.startswith(UTF8_SIG_BOM)
        assert "produktów" in csv_content
        assert "Marketing produktów;AGRO" in csv_content.replace("\r\n", "\n")

    def test_encode_uses_comma_delimiter_by_default(self):
        csv_content = CSVFormatter().encode([{"name": "Test", "identifier": "ABC"}])
        assert "Name,Identifier" in csv_content.replace("\r\n", "\n")

    def test_decode_roundtrip_with_polish_characters(self):
        formatter = CSVFormatter()
        original = [{"name": "Środki ochrony", "description": "Nawozy i nasiona"}]
        decoded = formatter.decode(formatter.encode(original))
        assert decoded[0]["name"] == "Środki ochrony"
        assert decoded[0]["description"] == "Nawozy i nasiona"

    def test_decode_strips_bom_from_uploaded_content(self):
        formatter = CSVFormatter()
        rows = formatter.decode(f"{UTF8_SIG_BOM}Name;Identifier\r\nTest;ABC\r\n")
        assert rows[0]["name"] == "Test"
        assert rows[0]["identifier"] == "ABC"

    def test_decode_detects_comma_delimiter_for_legacy_files(self):
        formatter = CSVFormatter()
        rows = formatter.decode("Name,Identifier\nTest,ABC\n")
        assert rows[0]["name"] == "Test"
        assert rows[0]["identifier"] == "ABC"

    def test_semicolon_roundtrip_preserves_polish_characters(self):
        formatter = CSVFormatter(delimiter=";")
        original = [{"name": "Marketing produktów", "description": "Nawozy i nasiona"}]
        decoded = formatter.decode(formatter.encode(original))
        assert decoded[0]["name"] == "Marketing produktów"
        assert decoded[0]["description"] == "Nawozy i nasiona"

    def test_encode_uses_crlf_line_endings(self):
        csv_content = CSVFormatter().encode([{"name": "Test"}])
        assert "\r\n" in csv_content

    def test_decode_accepts_semicolon_content_without_bom(self):
        rows = CSVFormatter().decode("Name;Identifier\r\nTest;ABC\r\n")
        assert rows[0]["name"] == "Test"
        assert rows[0]["identifier"] == "ABC"

    @pytest.mark.parametrize("with_bom", [True, False])
    def test_importer_decodes_uploaded_bytes_with_or_without_bom(self, with_bom):
        raw = "Name,Identifier\r\nŚrodki,ABC\r\n".encode("utf-8")
        if with_bom:
            raw = UTF8_SIG_BOM.encode("utf-8") + raw
        rows = DataImporter("csv").decode(raw)
        assert rows[0]["name"] == "Środki"
        assert rows[0]["identifier"] == "ABC"
