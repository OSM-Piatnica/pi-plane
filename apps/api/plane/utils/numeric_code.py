# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The numeric codes people type from an email: the one-time sign-in code, the sign-up and the email-change code.

Every one of them is guarded by the same kind of caps (a few wrong tries per code, a few codes per window), so the
length of the code is what keeps a guess from succeeding. It is set here once. Six digits left too small a code space
for those caps (upstream moved the sign-in code to eight in makeplane/plane#10301); a flow that generated its own
``secrets.randbelow(900000) + 100000`` was easy to leave behind.
"""

import secrets

CODE_DIGITS = 8


def generate_numeric_code(digits: int = CODE_DIGITS) -> str:
    """A random code of exactly ``digits`` decimal digits (the first one is never 0), from a CSPRNG."""
    lowest = 10 ** (digits - 1)
    return str(secrets.randbelow(9 * lowest) + lowest)
