/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { EIssueLayoutTypes } from "@plane/types";
import type { IProjectView } from "@plane/types";
import { LayoutSelection } from "@/components/issues/issue-layouts/filters";
import { WorkspaceListLayout } from "@/components/issues/issue-layouts/list/roots/workspace-root";
import { WorkspaceSpreadsheetRoot } from "@/components/issues/issue-layouts/spreadsheet/roots/workspace-root";

export type TWorkspaceLayoutProps = {
  activeLayout: EIssueLayoutTypes | undefined;
  isDefaultView: boolean;
  isLoading?: boolean;
  toggleLoading: (value: boolean) => void;
  workspaceSlug: string;
  globalViewId: string;
  routeFilters: {
    [key: string]: string;
  };
  fetchNextPages: () => void;
  globalViewsLoading: boolean;
  issuesLoading: boolean;
};

export function WorkspaceActiveLayout(props: TWorkspaceLayoutProps) {
  const {
    activeLayout = EIssueLayoutTypes.SPREADSHEET,
    isDefaultView,
    isLoading,
    toggleLoading,
    workspaceSlug,
    globalViewId,
    routeFilters,
    fetchNextPages,
    globalViewsLoading,
    issuesLoading,
  } = props;
  switch (activeLayout) {
    case EIssueLayoutTypes.SPREADSHEET:
      return (
        <WorkspaceSpreadsheetRoot
          isDefaultView={isDefaultView}
          isLoading={isLoading}
          toggleLoading={toggleLoading}
          workspaceSlug={workspaceSlug}
          globalViewId={globalViewId}
          routeFilters={routeFilters}
          fetchNextPages={fetchNextPages}
          globalViewsLoading={globalViewsLoading}
          issuesLoading={issuesLoading}
        />
      );
    default:
      return <WorkspaceAdditionalLayouts {...props} />;
  }
}

export type TLayoutSelectionProps = {
  onChange: (layout: EIssueLayoutTypes) => void;
  selectedLayout: EIssueLayoutTypes;
  workspaceSlug: string;
};

const GLOBAL_VIEW_LAYOUTS = [EIssueLayoutTypes.SPREADSHEET, EIssueLayoutTypes.LIST];

export function GlobalViewLayoutSelection(props: TLayoutSelectionProps) {
  const { onChange, selectedLayout } = props;
  return <LayoutSelection layouts={GLOBAL_VIEW_LAYOUTS} onChange={onChange} selectedLayout={selectedLayout} />;
}

export function WorkspaceAdditionalLayouts(props: TWorkspaceLayoutProps) {
  const { activeLayout, workspaceSlug, globalViewId } = props;
  if (activeLayout === EIssueLayoutTypes.LIST)
    return <WorkspaceListLayout workspaceSlug={workspaceSlug} globalViewId={globalViewId} />;
  return <></>;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function AdditionalHeaderItems(view: IProjectView) {
  return <></>;
}
