/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { EIssueLayoutTypes } from "@plane/types";
// components
import { LayoutErrorBoundary } from "@/components/common/layout-error-boundary";
import { CalendarLayoutLoader } from "@/components/ui/loader/layouts/calendar-layout-loader";
import { GanttLayoutLoader } from "@/components/ui/loader/layouts/gantt-layout-loader";
import { KanbanLayoutLoader } from "@/components/ui/loader/layouts/kanban-layout-loader";
import { ListLayoutLoader } from "@/components/ui/loader/layouts/list-layout-loader";
import { SpreadsheetLayoutLoader } from "@/components/ui/loader/layouts/spreadsheet-layout-loader";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
// local imports
import { IssueLayoutEmptyState } from "./empty-states";
import { IgnoredFiltersNotice } from "./ignored-filters-notice";

function ActiveLoader(props: { layout: EIssueLayoutTypes }) {
  const { layout } = props;
  switch (layout) {
    case EIssueLayoutTypes.LIST:
      return <ListLayoutLoader />;
    case EIssueLayoutTypes.KANBAN:
      return <KanbanLayoutLoader />;
    case EIssueLayoutTypes.SPREADSHEET:
      return <SpreadsheetLayoutLoader />;
    case EIssueLayoutTypes.CALENDAR:
      return <CalendarLayoutLoader />;
    case EIssueLayoutTypes.GANTT:
      return <GanttLayoutLoader />;
    default:
      return null;
  }
}

interface Props {
  children: string | React.ReactNode | React.ReactNode[];
  layout: EIssueLayoutTypes;
}

export const IssueLayoutHOC = observer(function IssueLayoutHOC(props: Props) {
  const { layout } = props;

  const storeType = useIssueStoreType();
  const { issues } = useIssues(storeType);

  const issueCount = issues.getGroupIssueCount(undefined, undefined, false);

  const isLoading = issues?.getIssueLoader() === "init-loader" || issueCount === undefined;
  const isEmpty = !isLoading && issueCount === 0 && layout !== EIssueLayoutTypes.CALENDAR;

  // the notice is outside of the loader and the empty state: the first fetch of a list happens behind the loader
  return (
    <>
      <IgnoredFiltersNotice />
      {isLoading ? (
        <ActiveLoader layout={layout} />
      ) : isEmpty ? (
        <IssueLayoutEmptyState storeType={storeType} />
      ) : (
        <LayoutErrorBoundary key={layout}>{props.children}</LayoutErrorBoundary>
      )}
    </>
  );
});
