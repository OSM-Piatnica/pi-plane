/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
// store hooks
// icons
import { TriangleIcon, SignalMediumIcon, Timer } from "lucide-react";
import {
  ArchiveOutline,
  AttachOutline,
  CalendarOutline,
  ChatOutline,
  CyclesOutline,
  DuplicateOfOutline,
  EpicOutline,
  GridOutline,
  IntakeOutline,
  LabelsOutline,
  LinkOutline,
  MembersOutline,
  ModuleOutline,
  RelatesToOutline,
  WorkItemsOutline,
} from "@makeplane/propel/icons";
import { BlockedIcon, BlockerIcon } from "@plane/blocks/icons";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { IIssueActivity } from "@plane/types";
import { generateWorkItemLink, capitalizeFirstLetter } from "@plane/utils";
// helpers
import { useLabel } from "@/hooks/store/use-label";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { renderTaggedText } from "@/helpers/tagged-text";
// types

type TTranslate = (key: string, params?: Record<string, unknown>) => string;
type TFormatDate = (date: string | Date | undefined | null) => string | undefined;

export function IssueLink({ activity }: { activity: IIssueActivity }) {
  // router params
  const { workspaceSlug } = useParams();
  const { isMobile } = usePlatformOS();
  const { t } = useTranslation();

  const workItemLink = generateWorkItemLink({
    workspaceSlug: workspaceSlug?.toString() ?? activity.workspace_detail?.slug,
    projectId: activity?.project,
    issueId: activity?.issue,
    projectIdentifier: activity?.project_detail?.identifier,
    sequenceId: activity?.issue_detail?.sequence_id,
  });

  return (
    <Tooltip
      label={activity?.issue_detail ? activity.issue_detail.name : t("activity_feed.profile.issue.deleted_tooltip")}
      layout="stacked"
      disabled={isMobile}
    >
      {activity?.issue_detail ? (
        <a
          aria-disabled={activity.issue === null}
          href={workItemLink}
          target={activity.issue === null ? "_self" : "_blank"}
          rel={activity.issue === null ? "" : "noopener noreferrer"}
          className="inline items-center gap-1 font-medium text-primary hover:underline"
        >
          <span className="whitespace-nowrap">{`${activity.project_detail.identifier}-${activity.issue_detail.sequence_id}`}</span>{" "}
          <span className="font-regular break-all">{activity.issue_detail?.name}</span>
        </a>
      ) : (
        <span className="inline-flex items-center gap-1 font-medium whitespace-nowrap text-primary">
          {` ${t("activity_feed.profile.issue.fallback_name")}`}{" "}
        </span>
      )}
    </Tooltip>
  );
}

function UserLink({ activity }: { activity: IIssueActivity }) {
  // router params
  const { workspaceSlug } = useParams();

  return (
    <a
      href={`/${workspaceSlug ?? activity.workspace_detail?.slug}/profile/${
        activity.new_identifier ?? activity.old_identifier
      }`}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center font-medium text-primary hover:underline"
    >
      {activity.new_value && activity.new_value !== "" ? activity.new_value : activity.old_value}
    </a>
  );
}

const LabelPill = observer(function LabelPill({ labelId, workspaceSlug }: { labelId: string; workspaceSlug: string }) {
  // store hooks
  const { workspaceLabels, fetchWorkspaceLabels } = useLabel();

  useEffect(() => {
    if (!workspaceLabels) fetchWorkspaceLabels(workspaceSlug);
  }, [fetchWorkspaceLabels, workspaceLabels, workspaceSlug]);

  return (
    <span
      className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
      style={{
        backgroundColor: workspaceLabels?.find((l) => l.id === labelId)?.color ?? "#000000",
      }}
      aria-hidden="true"
    />
  );
});

// renderers shared by the sentence templates
const issueTag = (activity: IIssueActivity) => ({ issue: () => <IssueLink activity={activity} /> });

const emphasisTag = (text: string | null | undefined, className: string) => ({
  value: () => <span className={className}>{text}</span>,
});

const NOWRAP_VALUE_CLASS = "font-medium whitespace-nowrap text-primary";

const entityLinkTag = (href: string, text: string | null | undefined) => ({
  value: () => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline items-center gap-1 font-medium text-primary hover:underline"
    >
      <span className="break-all">{text}</span>
    </a>
  ),
});

const labelTag = (labelId: string, workspaceSlug: string, text: string | null | undefined) => ({
  label: () => (
    <span className="inline-flex items-center gap-2 rounded-full border border-strong px-2 py-0.5 text-11">
      <LabelPill labelId={labelId} workspaceSlug={workspaceSlug} />
      <span className="line-clamp-1 flex-shrink font-medium break-all text-primary">{text}</span>
    </span>
  ),
});

const linkTag = (href: string | null | undefined) => ({
  link: (children: string) => (
    <a
      href={`${href}`}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
    >
      {children}
    </a>
  ),
});

const nowrapTag = { nowrap: (children: string) => <span className="whitespace-nowrap">{children}</span> };

const getInboxUserActivityMessage = (activity: IIssueActivity, showIssue: boolean, t: TTranslate): string => {
  switch (activity.verb) {
    case "-1":
      return showIssue
        ? t("activity_feed.profile.inbox.declined_with_issue")
        : t("activity_feed.profile.inbox.declined_without_issue");
    case "0":
      return showIssue
        ? t("activity_feed.profile.inbox.snoozed_with_issue")
        : t("activity_feed.profile.inbox.snoozed_without_issue");
    case "1":
      return showIssue
        ? t("activity_feed.profile.inbox.accepted_with_issue")
        : t("activity_feed.profile.inbox.accepted_without_issue");
    case "2":
      return showIssue
        ? t("activity_feed.profile.inbox.duplicate_with_issue")
        : t("activity_feed.profile.inbox.duplicate_without_issue");
    default:
      return showIssue
        ? t("activity_feed.profile.inbox.updated_with_issue")
        : t("activity_feed.profile.inbox.updated_without_issue");
  }
};

const getPriorityLabel = (priority: string | null | undefined, t: TTranslate): string => {
  switch (priority) {
    case undefined:
    case null:
    case "":
      return t("activity_feed.profile.priority.none");
    case "urgent":
      return t("activity_feed.profile.priority.urgent");
    case "high":
      return t("activity_feed.profile.priority.high");
    case "medium":
      return t("activity_feed.profile.priority.medium");
    case "low":
      return t("activity_feed.profile.priority.low");
    case "none":
      return t("activity_feed.profile.priority.none");
    default:
      return capitalizeFirstLetter(priority);
  }
};

const activityDetails: {
  [key: string]: {
    message: (
      activity: IIssueActivity,
      showIssue: boolean,
      workspaceSlug: string,
      t: TTranslate,
      formatDate: TFormatDate
    ) => React.ReactNode;
    icon: React.ReactNode;
  };
} = {
  assignees: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      const renderers = { ...issueTag(activity), assignee: () => <UserLink activity={activity} /> };
      if (activity.old_value === "")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.assignee.added_with_issue")
            : t("activity_feed.profile.assignee.added_without_issue"),
          renderers
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.assignee.removed_with_issue")
          : t("activity_feed.profile.assignee.removed_without_issue"),
        renderers
      );
    },
    icon: <MembersOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  archived_at: {
    message: (activity, _showIssue, _workspaceSlug, t) =>
      renderTaggedText(
        activity.new_value === "restore"
          ? t("activity_feed.profile.archived_at.restored")
          : t("activity_feed.profile.archived_at.archived"),
        issueTag(activity)
      ),
    icon: <ArchiveOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  attachment: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.verb === "created")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.attachment.added_with_issue")
            : t("activity_feed.profile.attachment.added_without_issue"),
          issueTag(activity)
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.attachment.removed_with_issue")
          : t("activity_feed.profile.attachment.removed_without_issue"),
        issueTag(activity)
      );
    },
    icon: <AttachOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  description: {
    message: (activity, showIssue, _workspaceSlug, t) =>
      renderTaggedText(
        showIssue
          ? t("activity_feed.profile.description.updated_with_issue")
          : t("activity_feed.profile.description.updated_without_issue"),
        issueTag(activity)
      ),
    icon: <ChatOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  estimate_point: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.estimate_point.removed_with_issue")
            : t("activity_feed.profile.estimate_point.removed_without_issue"),
          issueTag(activity)
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.estimate_point.set_with_issue")
          : t("activity_feed.profile.estimate_point.set_without_issue"),
        { ...issueTag(activity), value: () => activity.new_value }
      );
    },
    icon: <TriangleIcon size={12} className="text-secondary" aria-hidden="true" />,
  },
  issue: {
    message: (activity, _showIssue, _workspaceSlug, t) => {
      if (activity.verb === "created")
        return renderTaggedText(t("activity_feed.profile.issue.created"), issueTag(activity));
      if (activity.verb === "converted")
        return renderTaggedText(t("activity_feed.profile.issue.converted_to_epic"), issueTag(activity));
      return renderTaggedText(t("activity_feed.profile.issue.deleted"), issueTag(activity));
    },
    icon: <WorkItemsOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  epic: {
    message: (activity, _showIssue, _workspaceSlug, t) => {
      if (activity.verb === "created")
        return renderTaggedText(t("activity_feed.profile.epic.created"), issueTag(activity));
      if (activity.verb === "converted")
        return renderTaggedText(t("activity_feed.profile.epic.converted_to_work_item"), issueTag(activity));
      return renderTaggedText(t("activity_feed.profile.epic.deleted"), issueTag(activity));
    },
    icon: <EpicOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  labels: {
    message: (activity, showIssue, workspaceSlug, t) => {
      if (activity.old_value === "")
        return (
          <span className="overflow-hidden">
            {renderTaggedText(
              showIssue
                ? t("activity_feed.profile.label.added_with_issue")
                : t("activity_feed.profile.label.added_without_issue"),
              {
                ...issueTag(activity),
                ...labelTag(activity.new_identifier ?? "", workspaceSlug, activity.new_value),
              }
            )}
          </span>
        );
      return (
        <>
          {renderTaggedText(
            showIssue
              ? t("activity_feed.profile.label.removed_with_issue")
              : t("activity_feed.profile.label.removed_without_issue"),
            {
              ...issueTag(activity),
              ...labelTag(activity.old_identifier ?? "", workspaceSlug, activity.old_value),
            }
          )}
        </>
      );
    },
    icon: <LabelsOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  link: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.verb === "created")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.link.added_with_issue")
            : t("activity_feed.profile.link.added_without_issue"),
          { ...issueTag(activity), ...linkTag(activity.new_value) }
        );
      if (activity.verb === "updated")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.link.updated_with_issue")
            : t("activity_feed.profile.link.updated_without_issue"),
          { ...issueTag(activity), ...linkTag(activity.old_value) }
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.link.removed_with_issue")
          : t("activity_feed.profile.link.removed_without_issue"),
        { ...issueTag(activity), ...linkTag(activity.old_value) }
      );
    },
    icon: <LinkOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  cycles: {
    message: (activity, showIssue, workspaceSlug, t) => {
      const base = `/${workspaceSlug}/projects/${activity.project}/cycles/`;
      if (activity.verb === "created")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.cycle.added_with_issue")
            : t("activity_feed.profile.cycle.added_without_issue"),
          {
            ...issueTag(activity),
            ...nowrapTag,
            ...entityLinkTag(`${base}${activity.new_identifier}`, activity.new_value),
          }
        );
      if (activity.verb === "updated")
        return renderTaggedText(t("activity_feed.profile.cycle.set"), {
          ...nowrapTag,
          ...entityLinkTag(`${base}${activity.new_identifier}`, activity.new_value),
        });
      return renderTaggedText(t("activity_feed.profile.cycle.removed"), {
        ...issueTag(activity),
        ...entityLinkTag(`${base}${activity.old_identifier}`, activity.old_value),
      });
    },
    icon: <CyclesOutline height={12} width={12} className="text-secondary" aria-hidden="true" />,
  },
  modules: {
    message: (activity, showIssue, workspaceSlug, t) => {
      const base = `/${workspaceSlug}/projects/${activity.project}/modules/`;
      if (activity.verb === "created")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.module.added_with_issue")
            : t("activity_feed.profile.module.added_without_issue"),
          { ...issueTag(activity), ...entityLinkTag(`${base}${activity.new_identifier}`, activity.new_value) }
        );
      if (activity.verb === "updated")
        return renderTaggedText(
          t("activity_feed.profile.module.set"),
          entityLinkTag(`${base}${activity.new_identifier}`, activity.new_value)
        );
      return renderTaggedText(t("activity_feed.profile.module.removed"), {
        ...issueTag(activity),
        ...entityLinkTag(`${base}${activity.old_identifier}`, activity.old_value),
      });
    },
    icon: <ModuleOutline className="h-3 w-3 !text-secondary" aria-hidden="true" />,
  },
  name: {
    message: (activity, showIssue, _workspaceSlug, t) =>
      renderTaggedText(
        showIssue ? t("activity_feed.profile.name.set_with_issue") : t("activity_feed.profile.name.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(activity.new_value, "break-all") }
      ),
    icon: <ChatOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  parent: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.parent.removed_with_issue")
            : t("activity_feed.profile.parent.removed_without_issue"),
          { ...issueTag(activity), ...emphasisTag(activity.old_value, NOWRAP_VALUE_CLASS) }
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.parent.set_with_issue")
          : t("activity_feed.profile.parent.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(activity.new_value, NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <MembersOutline className="h-3 w-3 !text-secondary" aria-hidden="true" />,
  },
  priority: {
    message: (activity, showIssue, _workspaceSlug, t) =>
      renderTaggedText(
        showIssue
          ? t("activity_feed.profile.priority.set_with_issue")
          : t("activity_feed.profile.priority.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(getPriorityLabel(activity.new_value, t), "font-medium text-primary") }
      ),
    icon: <SignalMediumIcon size={12} className="text-secondary" aria-hidden="true" />,
  },
  relates_to: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.old_value === "")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.relates_to.added_with_issue")
            : t("activity_feed.profile.relates_to.added_without_issue"),
          { ...issueTag(activity), ...emphasisTag(activity.new_value, NOWRAP_VALUE_CLASS) }
        );
      return renderTaggedText(
        t("activity_feed.profile.relates_to.removed"),
        emphasisTag(activity.old_value, NOWRAP_VALUE_CLASS)
      );
    },
    icon: <RelatesToOutline height="12" width="12" className="text-secondary" />,
  },
  blocking: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.old_value === "")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.blocking.added_with_issue")
            : t("activity_feed.profile.blocking.added_without_issue"),
          { ...issueTag(activity), ...emphasisTag(activity.new_value, NOWRAP_VALUE_CLASS) }
        );
      return renderTaggedText(
        t("activity_feed.profile.blocking.removed"),
        emphasisTag(activity.old_value, NOWRAP_VALUE_CLASS)
      );
    },
    icon: <BlockerIcon height="12" width="12" className="text-secondary" />,
  },
  blocked_by: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.old_value === "")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.blocked_by.added_with_issue")
            : t("activity_feed.profile.blocked_by.added_without_issue"),
          { ...issueTag(activity), ...emphasisTag(activity.new_value, NOWRAP_VALUE_CLASS) }
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.blocked_by.removed_with_issue")
          : t("activity_feed.profile.blocked_by.removed_without_issue"),
        { ...issueTag(activity), ...emphasisTag(activity.old_value, NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <BlockedIcon height="12" width="12" className="text-secondary" />,
  },
  duplicate: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (activity.old_value === "")
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.duplicate.added_with_issue")
            : t("activity_feed.profile.duplicate.added_without_issue"),
          { ...issueTag(activity), ...emphasisTag(activity.new_value, NOWRAP_VALUE_CLASS) }
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.duplicate.removed_with_issue")
          : t("activity_feed.profile.duplicate.removed_without_issue"),
        { ...issueTag(activity), ...emphasisTag(activity.old_value, NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <DuplicateOfOutline width={12} height={12} className="text-secondary" />,
  },
  state: {
    message: (activity, showIssue, _workspaceSlug, t) =>
      renderTaggedText(
        showIssue
          ? t("activity_feed.profile.state.set_with_issue")
          : t("activity_feed.profile.state.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(activity.new_value, "font-medium break-all text-primary") }
      ),
    icon: <GridOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  start_date: {
    message: (activity, showIssue, _workspaceSlug, t, formatDate) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.start_date.removed_with_issue")
            : t("activity_feed.profile.start_date.removed_without_issue"),
          issueTag(activity)
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.start_date.set_with_issue")
          : t("activity_feed.profile.start_date.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(formatDate(activity.new_value), NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <CalendarOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  finish_date: {
    message: (activity, showIssue, _workspaceSlug, t, formatDate) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.finish_date.removed_with_issue")
            : t("activity_feed.profile.finish_date.removed_without_issue"),
          issueTag(activity)
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.finish_date.set_with_issue")
          : t("activity_feed.profile.finish_date.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(formatDate(activity.new_value), NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <CalendarOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  target_date: {
    message: (activity, showIssue, _workspaceSlug, t, formatDate) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.target_date.removed_with_issue")
            : t("activity_feed.profile.target_date.removed_without_issue"),
          issueTag(activity)
        );
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.target_date.set_with_issue")
          : t("activity_feed.profile.target_date.set_without_issue"),
        { ...issueTag(activity), ...emphasisTag(formatDate(activity.new_value), NOWRAP_VALUE_CLASS) }
      );
    },
    icon: <CalendarOutline width={12} height={12} className="text-secondary" aria-hidden="true" />,
  },
  duration: {
    message: (activity, showIssue, _workspaceSlug, t) => {
      if (!activity.new_value)
        return renderTaggedText(
          showIssue
            ? t("activity_feed.profile.duration.removed_with_issue")
            : t("activity_feed.profile.duration.removed_without_issue"),
          issueTag(activity)
        );
      const days = Number(activity.new_value);
      return renderTaggedText(
        showIssue
          ? t("activity_feed.profile.duration.set_with_issue")
          : t("activity_feed.profile.duration.set_without_issue"),
        {
          ...issueTag(activity),
          ...emphasisTag(t("activity_feed.profile.duration.days", { count: days }), NOWRAP_VALUE_CLASS),
        }
      );
    },
    icon: <Timer size={12} className="text-secondary" aria-hidden="true" />,
  },
  inbox: {
    message: (activity, showIssue, _workspaceSlug, t) =>
      renderTaggedText(getInboxUserActivityMessage(activity, showIssue, t), issueTag(activity)),
    icon: <IntakeOutline className="size-3 text-secondary" aria-hidden="true" />,
  },
};

export function ActivityIcon({ activity }: { activity: IIssueActivity }) {
  return <>{activityDetails[activity.field as keyof typeof activityDetails]?.icon}</>;
}

type ActivityMessageProps = {
  activity: IIssueActivity;
  showIssue?: boolean;
};

export function ActivityMessage({ activity, showIssue = false }: ActivityMessageProps) {
  // router params
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();
  const activityField = activity.field ?? "issue";

  return (
    <>
      {activityDetails[activityField as keyof typeof activityDetails]?.message(
        activity,
        showIssue,
        workspaceSlug ? workspaceSlug.toString() : (activity.workspace_detail?.slug ?? ""),
        t,
        formatDate
      )}
    </>
  );
}
