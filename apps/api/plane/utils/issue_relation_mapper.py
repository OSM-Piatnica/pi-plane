# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from plane.utils.issue_relation_types import INVERSE_RELATIONS, MIRRORED_RELATIONS


def get_inverse_relation(relation_type):
    return INVERSE_RELATIONS.get(relation_type, relation_type)


def get_actual_relation(relation_type):
    # This function is used to get the actual relation type which is stored in database
    if relation_type in MIRRORED_RELATIONS:
        return INVERSE_RELATIONS[relation_type]
    return relation_type
