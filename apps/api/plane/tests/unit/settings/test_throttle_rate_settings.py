# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The anon and per-asset duplicate throttles are configurable, defaulting to 180 and 60 per minute."""

import os

import pytest
from django.conf import settings

from plane.throttles.asset import AssetRateThrottle


@pytest.mark.unit
def test_setting_follows_env_or_defaults_to_60_per_minute():
    expected = os.environ.get("ASSET_DUPLICATE_RATE_LIMIT", "60/minute")
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["asset_id"] == expected


@pytest.mark.unit
@pytest.mark.skipif("ASSET_DUPLICATE_RATE_LIMIT" in os.environ, reason="env override in effect")
def test_default_throttle_allows_60_requests_per_minute():
    throttle = AssetRateThrottle()
    assert (throttle.num_requests, throttle.duration) == (60, 60)


@pytest.mark.unit
def test_throttle_is_keyed_per_asset_not_per_user():
    class View:
        kwargs = {"asset_id": "abc"}

    assert AssetRateThrottle().get_cache_key(request=None, view=View()) == "throttle_asset_abc"


@pytest.mark.unit
def test_anon_setting_follows_env_or_defaults_to_180_per_minute():
    expected = os.environ.get("ANON_RATE_LIMIT", "180/minute")
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] == expected
