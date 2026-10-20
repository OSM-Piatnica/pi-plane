/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import {
  ClockOutline,
  CloseCircleOutline,
  CopyOutline,
  TickCircleOutline,
  WarningTriangleOutline,
} from "@makeplane/propel/icons";
import { EInboxIssueStatus } from "@plane/types";

export const ICON_PROPERTIES = {
  [EInboxIssueStatus.PENDING]: {
    icon: WarningTriangleOutline,
    textColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "text-warning-primary"),
    bgColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "bg-warning-subtle"),
  },
  [EInboxIssueStatus.DECLINED]: {
    icon: CloseCircleOutline,
    textColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "text-danger-primary"),
    bgColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "bg-danger-subtle"),
  },
  [EInboxIssueStatus.SNOOZED]: {
    icon: ClockOutline,
    textColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "text-danger-primary" : "text-placeholder"),
    bgColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "bg-danger-subtle" : "bg-layer-3"),
  },
  [EInboxIssueStatus.ACCEPTED]: {
    icon: TickCircleOutline,
    textColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "text-success-primary"),
    bgColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "bg-success-subtle"),
  },
  [EInboxIssueStatus.DUPLICATE]: {
    icon: CopyOutline,
    textColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "text-secondary"),
    bgColor: (snoozeDatePassed: boolean = false) => (snoozeDatePassed ? "" : "bg-layer-3"),
  },
};
