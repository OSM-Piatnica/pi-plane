# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

import csv
from io import StringIO

import pytest

from plane.utils.porters.formatters import CSVFormatter, strip_utf8_bom


def _read_rows(content):
    # The fork's CSVFormatter prepends a UTF-8 BOM; strip it so it isn't read as part of the first cell.
    return list(csv.reader(StringIO(strip_utf8_bom(content))))


@pytest.mark.unit
class TestPorterCSVFormatterSanitization:
    """CSV exports must not emit formula-triggering values, including in header rows."""

    def test_data_values_are_sanitized(self):
        content = CSVFormatter().encode([{"name": "=1+2"}])
        rows = _read_rows(content)
        assert rows[1][0] == "'=1+2"

    def test_prettified_headers_are_sanitized(self):
        content = CSVFormatter().encode([{"=evil_header": "value"}])
        rows = _read_rows(content)
        assert rows[0][0] == "'=Evil Header"

    def test_raw_headers_are_sanitized(self):
        content = CSVFormatter(prettify_headers=False).encode([{"=evil": "value"}])
        rows = _read_rows(content)
        assert rows[0][0] == "'=evil"
