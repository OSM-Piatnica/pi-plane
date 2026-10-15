# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from types import SimpleNamespace
from unittest import mock

import pytest

from plane.license.bgtasks import telemetry_metrics
from plane.license.models import Instance


@pytest.mark.unit
class TestTelemetryOptIn:
    def test_new_instances_do_not_report_by_default(self):
        assert Instance._meta.get_field("is_telemetry_enabled").default is False

    @pytest.mark.parametrize("instance", [None, SimpleNamespace(is_telemetry_enabled=False)])
    def test_push_is_skipped_unless_enabled(self, instance):
        """No instance, or telemetry off: nothing is configured and nothing is sent."""
        with (
            mock.patch.object(telemetry_metrics, "Instance") as instance_model,
            mock.patch.object(telemetry_metrics, "MeterProvider") as meter_provider,
            mock.patch.object(telemetry_metrics, "_create_otlp_metric_exporter") as exporter,
        ):
            instance_model.objects.first.return_value = instance

            telemetry_metrics._collect_and_push_metrics()

        meter_provider.assert_not_called()
        exporter.assert_not_called()
