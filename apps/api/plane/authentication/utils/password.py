# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Third party imports
from zxcvbn import zxcvbn

# Score at most this many characters from each end of the password, so the cost of
# scoring stays bounded. The password is strong if either window is strong.
ZXCVBN_MAX_LENGTH = 128


def is_password_strong(password):
    windows = {password[:ZXCVBN_MAX_LENGTH], password[-ZXCVBN_MAX_LENGTH:]}
    # zxcvbn >= 4.5.0 raises ValueError for inputs longer than its own max_length (default 72), so
    # the limit is raised to the window size.
    return any(zxcvbn(window, max_length=ZXCVBN_MAX_LENGTH)["score"] >= 3 for window in windows)
