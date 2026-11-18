# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Query parameters of the public boards."""

# Filters only the app offers. `epic` walks up the parent chain of the work items, which a public request must not
# be able to start, and a public board has no Epic grouping to load more of.
APP_ONLY_FILTER_PARAMS = ("epic",)


def public_filter_params(query_params):
    """A copy of the query parameters without the filters that only the app offers."""

    params = query_params.copy()
    for name in APP_ONLY_FILTER_PARAMS:
        params.pop(name, None)
    return params
