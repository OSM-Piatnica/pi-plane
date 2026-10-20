/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { BlockingOutline, CloseCircleOutline, DuplicateOfOutline, RelatesToOutline } from "@makeplane/propel/icons";
import type { TRelationObject } from "@/components/issues/issue-detail-widgets/relations";
import type { TIssueRelationTypes } from "@plane/types";
import { CalendarAfterIcon, CalendarBeforeIcon } from "@plane/blocks/icons";

export const ISSUE_RELATION_OPTIONS: Record<TIssueRelationTypes, TRelationObject> = {
  relates_to: {
    key: "relates_to",
    i18n_label: "issue.relation.relates_to",
    className: "bg-layer-1 text-secondary",
    icon: (size) => <RelatesToOutline height={size} width={size} className="text-secondary" />,
    i18n_placeholder: "issue_ui.add_related_work_items",
  },
  duplicate: {
    key: "duplicate",
    i18n_label: "issue.relation.duplicate",
    className: "bg-layer-1 text-secondary",
    icon: (size) => <DuplicateOfOutline width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  blocked_by: {
    key: "blocked_by",
    i18n_label: "issue.relation.blocked_by",
    className: "bg-danger-subtle text-danger-primary",
    icon: (size) => <BlockingOutline width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  blocking: {
    key: "blocking",
    i18n_label: "issue.relation.blocking",
    className: "bg-yellow-500/20 text-yellow-700",
    icon: (size) => <CloseCircleOutline width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  start_before: {
    key: "start_before",
    i18n_label: "issue.relation.start_before",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarBeforeIcon width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  start_after: {
    key: "start_after",
    i18n_label: "issue.relation.start_after",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarAfterIcon width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  finish_before: {
    key: "finish_before",
    i18n_label: "issue.relation.finish_before",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarBeforeIcon width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
  finish_after: {
    key: "finish_after",
    i18n_label: "issue.relation.finish_after",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarAfterIcon width={size} height={size} className="text-secondary" />,
    i18n_placeholder: "common.none",
  },
};

export const useTimeLineRelationOptions = () => ISSUE_RELATION_OPTIONS;
