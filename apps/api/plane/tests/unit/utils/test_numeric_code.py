# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The numeric codes people type from an email are as long as the one place that sets it says."""

from unittest.mock import patch

import pytest

from plane.utils.numeric_code import CODE_DIGITS, generate_numeric_code


@pytest.mark.unit
class TestGenerateNumericCode:
    def test_is_eight_digits_by_default(self):
        assert CODE_DIGITS == 8
        assert len(generate_numeric_code()) == 8

    @pytest.mark.parametrize("digits", [4, 6, 8, 10])
    def test_has_exactly_the_digits_asked_for_and_never_starts_with_zero(self, digits):
        for _ in range(200):
            code = generate_numeric_code(digits)
            assert code.isdecimal() and len(code) == digits and code[0] != "0"

    def test_covers_the_whole_range(self):
        with patch("plane.utils.numeric_code.secrets.randbelow", return_value=0):
            assert generate_numeric_code(6) == "100000"
        with patch("plane.utils.numeric_code.secrets.randbelow", return_value=900000 - 1):
            assert generate_numeric_code(6) == "999999"

    def test_asks_the_secrets_module_for_the_whole_space(self):
        with patch("plane.utils.numeric_code.secrets.randbelow", return_value=0) as randbelow:
            generate_numeric_code()
        randbelow.assert_called_once_with(9 * 10**7)
