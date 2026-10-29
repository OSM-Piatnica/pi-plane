# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""How large a spreadsheet import may be, as the instance administrator set it.

Two limits, both changed on the General page of the admin app and stored as instance configurations: the size of
the uploaded file (bytes) and the number of work items in it. An import is read and written within one request, so
the number of work items has a ceiling of its own. Until a value is saved, or when it is empty, the defaults here apply.
"""

from plane.utils.file_size_limit import MIN_FILE_SIZE_LIMIT, get_file_size_limit_max, get_saved_number

FILE_SIZE_KEY = "IMPORT_FILE_SIZE_LIMIT"
MAX_WORK_ITEMS_KEY = "IMPORT_MAX_WORK_ITEMS"

DEFAULT_IMPORT_FILE_SIZE_LIMIT = 15 * 1024 * 1024
DEFAULT_IMPORT_MAX_WORK_ITEMS = 500
MIN_IMPORT_MAX_WORK_ITEMS = 1
MAX_IMPORT_MAX_WORK_ITEMS = 5000


def get_import_file_size_limit_max() -> int:
    """The file is a request body, so it cannot be larger than the proxy accepts."""
    return get_file_size_limit_max()


def get_import_file_size_limit() -> int:
    value = get_saved_number(FILE_SIZE_KEY)
    ceiling = get_import_file_size_limit_max()
    if value is None:
        return min(DEFAULT_IMPORT_FILE_SIZE_LIMIT, ceiling)
    return max(MIN_FILE_SIZE_LIMIT, min(value, ceiling))


def get_import_max_work_items() -> int:
    value = get_saved_number(MAX_WORK_ITEMS_KEY)
    if value is None:
        return DEFAULT_IMPORT_MAX_WORK_ITEMS
    return max(MIN_IMPORT_MAX_WORK_ITEMS, min(value, MAX_IMPORT_MAX_WORK_ITEMS))
