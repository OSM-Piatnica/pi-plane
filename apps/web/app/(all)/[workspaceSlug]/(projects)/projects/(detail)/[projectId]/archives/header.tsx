/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { ArchiveOutline, CyclesOutline, ModuleOutline, WorkItemsOutline } from "@makeplane/propel/icons";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { EIssuesStoreType } from "@plane/types";
// ui
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { Header } from "@plane/blocks/layout";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { CommonProjectBreadcrumbs } from "@/components/breadcrumbs/common";
import { useProjectCrumbProps } from "@/components/breadcrumbs/use-project-crumb-props";
import { useTranslation } from "@plane/i18n";

type TProps = {
  activeTab: "issues" | "cycles" | "modules";
};

const PROJECT_ARCHIVES_BREADCRUMB_LIST: {
  [key: string]: {
    i18n_label: string;
    href: string;
    icon: React.FC<React.SVGAttributes<SVGElement> & { className?: string }>;
  };
} = {
  issues: {
    i18n_label: "common.work_items",
    href: "/issues",
    icon: WorkItemsOutline,
  },
  cycles: {
    i18n_label: "common.cycles",
    href: "/cycles",
    icon: CyclesOutline,
  },
  modules: {
    i18n_label: "common.modules",
    href: "/modules",
    icon: ModuleOutline,
  },
};

export const ProjectArchivesHeader = observer(function ProjectArchivesHeader(props: TProps) {
  const { activeTab } = props;
  // translation
  const { t } = useTranslation();
  // router
  const { workspaceSlug, projectId } = useParams();
  const projectCrumb = useProjectCrumbProps(workspaceSlug?.toString(), projectId?.toString());
  // store hooks
  const {
    issues: { getGroupIssueCount },
  } = useIssues(EIssuesStoreType.ARCHIVED);
  const { loader } = useProject();
  // hooks
  const { isMobile } = usePlatformOS();

  const issueCount = getGroupIssueCount(undefined, undefined, false);

  const activeTabBreadcrumbDetail =
    PROJECT_ARCHIVES_BREADCRUMB_LIST[activeTab as keyof typeof PROJECT_ARCHIVES_BREADCRUMB_LIST];

  return (
    <Header>
      <Header.LeftItem>
        <div className="flex items-center gap-2.5">
          <Breadcrumbs isLoading={loader === "init-loader"}>
            <CommonProjectBreadcrumbs
              workspaceSlug={workspaceSlug?.toString()}
              projectId={projectId?.toString()}
              {...projectCrumb}
            />
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink
                  href={`/${workspaceSlug}/projects/${projectId}/archives/issues`}
                  label={t("archives")}
                  icon={<ArchiveOutline className="h-4 w-4 text-tertiary" />}
                />
              }
            />
            {activeTabBreadcrumbDetail && (
              <Breadcrumbs.Item
                component={
                  <BreadcrumbLink
                    label={t(activeTabBreadcrumbDetail.i18n_label)}
                    icon={<activeTabBreadcrumbDetail.icon className="h-4 w-4 text-tertiary" />}
                  />
                }
              />
            )}
          </Breadcrumbs>
          {activeTab === "issues" && issueCount && issueCount > 0 ? (
            <Tooltip
              label={t("issue_ui.archived_work_items_count", { count: issueCount })}
              layout="stacked"
              side="bottom"
              disabled={isMobile}
            >
              <span className="flex flex-shrink-0 cursor-default items-center justify-center rounded-xl bg-accent-primary/20 px-2.5 py-0.5 text-center text-11 font-semibold text-accent-primary">
                {issueCount}
              </span>
            </Tooltip>
          ) : null}
        </div>
      </Header.LeftItem>
    </Header>
  );
});
