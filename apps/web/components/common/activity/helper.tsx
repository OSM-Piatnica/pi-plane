/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { FC, ReactNode } from "react";
import {
  AlignLeftOutline,
  ArchiveOutline,
  AttachOutline,
  ClockOutline,
  CyclesOutline,
  DocumentationOutline,
  DueDateOutline,
  EstimateOutline,
  GitBranchOutline,
  GlobeOutline,
  GridOutline,
  HashOutline,
  HierarchyOutline,
  InboxOutline,
  IntakeOutline,
  LabelsOutline,
  LinkOutline,
  MembersOutline,
  ModuleOutline,
  PriorityOutline,
  RefreshOutline,
  StartDateOutline,
  StateOutline,
  SubscribeOutline,
  TextOutline,
  TimeTrackingOutline,
  ToDoOutline,
  WorkItemsOutline,
} from "@makeplane/propel/icons";
// components

import { renderTaggedText } from "@/helpers/tagged-text";
import { store } from "@/lib/store-context";
import type { TProjectActivity } from "@plane/types";

type ActivityIconMap = {
  [key: string]: FC<{ className?: string }>;
};
export const iconsMap: ActivityIconMap = {
  priority: PriorityOutline,
  archived_at: ArchiveOutline,
  restored: RefreshOutline,
  link: LinkOutline,
  start_date: StartDateOutline,
  target_date: DueDateOutline,
  label: LabelsOutline,
  inbox: InboxOutline,
  description: AlignLeftOutline,
  assignee: MembersOutline,
  attachment: AttachOutline,
  name: TextOutline,
  state: StateOutline,
  estimate: EstimateOutline,
  cycle: CyclesOutline,
  module: ModuleOutline,
  page: DocumentationOutline,
  network: GlobeOutline,
  identifier: HashOutline,
  timezone: ClockOutline,
  is_project_updates_enabled: SubscribeOutline,
  is_epic_enabled: GridOutline,
  is_workflow_enabled: GitBranchOutline,
  is_time_tracking_enabled: TimeTrackingOutline,
  is_issue_type_enabled: ToDoOutline,
  default: HierarchyOutline,
  module_view: ModuleOutline,
  cycle_view: CyclesOutline,
  issue_views_view: WorkItemsOutline,
  page_view: DocumentationOutline,
  intake_view: IntakeOutline,
};

type TTranslate = (key: string, params?: Record<string, unknown>) => string;

const valueClass = "font-medium text-primary";

// picks the enabled / disabled sentence from the raw "true" / "false" value, else the verb fallback
const booleanText = (value: string | undefined, enabled: string, disabled: string, fallback: string) => {
  if (value === "true") return enabled;
  if (value === "false") return disabled;
  return fallback;
};

export const messages = (
  activity: TProjectActivity,
  t: TTranslate
): { message: string | ReactNode; customUserName?: string } => {
  const activityType = activity.field;
  const newValue = activity.new_value;
  const oldValue = activity.old_value;
  const verb = activity.verb;
  const workspaceDetail = store.workspaceRoot.getWorkspaceById(activity.workspace);

  // renders a sentence template, putting the styled value where its `<value/>` placeholder is
  const withValue = (template: string, value: ReactNode) =>
    renderTaggedText(template, { value: () => <span className={valueClass}>{value}</span> });

  switch (activityType) {
    case "priority":
      return {
        message: withValue(t("activity_feed.project.priority.set"), newValue || t("activity_feed.project.value_none")),
      };
    case "archived_at":
      return {
        message:
          newValue === "restore"
            ? t("activity_feed.project.archived_at.restored")
            : t("activity_feed.project.archived_at.archived"),
        customUserName: newValue === "archive" ? "Plane" : undefined,
      };
    case "name":
      return { message: withValue(t("activity_feed.project.name.renamed"), newValue) };
    case "description":
      return {
        message: newValue
          ? t("activity_feed.project.description.updated")
          : t("activity_feed.project.description.removed"),
      };
    case "start_date":
      return {
        message: newValue
          ? withValue(t("activity_feed.project.start_date.set"), newValue)
          : t("activity_feed.project.start_date.removed"),
      };
    case "target_date":
      return {
        message: newValue
          ? withValue(t("activity_feed.project.target_date.set"), newValue)
          : t("activity_feed.project.target_date.removed"),
      };
    case "state":
      return {
        message: withValue(t("activity_feed.project.state.set"), newValue || t("activity_feed.project.value_none")),
      };
    case "estimate":
      if (newValue) return { message: withValue(t("activity_feed.project.estimate.set"), newValue) };
      return {
        message: oldValue
          ? withValue(t("activity_feed.project.estimate.removed_with_value"), oldValue)
          : t("activity_feed.project.estimate.removed"),
      };
    case "cycles": {
      if (verb === "removed") {
        return {
          message: withValue(
            t("activity_feed.project.cycles.removed"),
            activity.old_value || t("activity_feed.project.cycles.unknown")
          ),
        };
      }
      return {
        message: renderTaggedText(t("activity_feed.project.cycles.added"), {
          value: () => (
            <a
              href={`/${workspaceDetail?.slug}/projects/${activity.project}/cycles/${activity.new_identifier}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex font-medium text-primary"
            >
              {activity.new_value}
            </a>
          ),
        }),
      };
    }
    case "modules":
      return {
        message:
          verb === "removed"
            ? withValue(t("activity_feed.project.modules.removed"), oldValue)
            : withValue(
                t("activity_feed.project.modules.added"),
                newValue || t("activity_feed.project.modules.unknown")
              ),
      };
    case "labels": {
      const label = newValue || oldValue || t("activity_feed.project.labels.untitled");
      if (verb === "created") return { message: withValue(t("activity_feed.project.labels.created"), label) };
      if (verb === "added") return { message: withValue(t("activity_feed.project.labels.added"), label) };
      if (verb === "removed") return { message: withValue(t("activity_feed.project.labels.removed"), label) };
      if (verb === "deleted") return { message: withValue(t("activity_feed.project.labels.deleted"), label) };
      return { message: withValue(t("activity_feed.project.labels.updated"), label) };
    }
    case "inbox":
      return {
        message: newValue ? t("activity_feed.project.inbox.enabled") : t("activity_feed.project.inbox.disabled"),
      };
    case "page":
      return {
        message: newValue
          ? withValue(t("activity_feed.project.page.created"), newValue)
          : withValue(t("activity_feed.project.page.removed"), oldValue || t("activity_feed.project.page.untitled")),
      };
    case "network":
      return {
        message: newValue ? t("activity_feed.project.network.enabled") : t("activity_feed.project.network.disabled"),
      };
    case "identifier":
      return {
        message: withValue(
          t("activity_feed.project.identifier.updated"),
          newValue || t("activity_feed.project.value_none")
        ),
      };
    case "timezone":
      return {
        message: withValue(
          t("activity_feed.project.timezone.changed"),
          newValue || t("activity_feed.project.timezone.default")
        ),
      };
    case "module_view":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.module_view.enabled"),
          t("activity_feed.project.module_view.disabled"),
          t("activity_feed.project.module_view.fallback", { verb })
        ),
      };
    case "cycle_view":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.cycle_view.enabled"),
          t("activity_feed.project.cycle_view.disabled"),
          t("activity_feed.project.cycle_view.fallback", { verb })
        ),
      };
    case "issue_views_view":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.issue_views_view.enabled"),
          t("activity_feed.project.issue_views_view.disabled"),
          t("activity_feed.project.issue_views_view.fallback", { verb })
        ),
      };
    case "page_view":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.page_view.enabled"),
          t("activity_feed.project.page_view.disabled"),
          t("activity_feed.project.page_view.fallback", { verb })
        ),
      };
    case "intake_view":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.intake_view.enabled"),
          t("activity_feed.project.intake_view.disabled"),
          t("activity_feed.project.intake_view.fallback", { verb })
        ),
      };
    case "is_project_updates_enabled":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.is_project_updates_enabled.enabled"),
          t("activity_feed.project.is_project_updates_enabled.disabled"),
          t("activity_feed.project.is_project_updates_enabled.fallback", { verb })
        ),
      };
    case "is_epic_enabled":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.is_epic_enabled.enabled"),
          t("activity_feed.project.is_epic_enabled.disabled"),
          t("activity_feed.project.is_epic_enabled.fallback", { verb })
        ),
      };
    case "is_workflow_enabled":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.is_workflow_enabled.enabled"),
          t("activity_feed.project.is_workflow_enabled.disabled"),
          t("activity_feed.project.is_workflow_enabled.fallback", { verb })
        ),
      };
    case "is_time_tracking_enabled":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.is_time_tracking_enabled.enabled"),
          t("activity_feed.project.is_time_tracking_enabled.disabled"),
          t("activity_feed.project.is_time_tracking_enabled.fallback", { verb })
        ),
      };
    case "is_issue_type_enabled":
      return {
        message: booleanText(
          newValue,
          t("activity_feed.project.is_issue_type_enabled.enabled"),
          t("activity_feed.project.is_issue_type_enabled.disabled"),
          t("activity_feed.project.is_issue_type_enabled.fallback", { verb })
        ),
      };
    default:
      return {
        message: t("activity_feed.project.default", { verb, field: activityType?.replace(/_/g, " ") }),
      };
  }
};
