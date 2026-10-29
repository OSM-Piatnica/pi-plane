/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
// types
import type { IProject } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useTranslation } from "@plane/i18n";

const ARCHIVES_TAB_LIST: {
  key: string;
  i18n_label: string;
  shouldRender: (projectDetails: IProject) => boolean;
}[] = [
  {
    key: "issues",
    i18n_label: "common.work_items",
    shouldRender: () => true,
  },
  {
    key: "cycles",
    i18n_label: "common.cycles",
    shouldRender: (projectDetails) => projectDetails.cycle_view,
  },
  {
    key: "modules",
    i18n_label: "common.modules",
    shouldRender: (projectDetails) => projectDetails.module_view,
  },
];

export const ArchiveTabsList = observer(function ArchiveTabsList() {
  // translation
  const { t } = useTranslation();
  // router
  const { workspaceSlug, projectId } = useParams();
  const pathname = usePathname();
  // store hooks
  const { getProjectById } = useProject();

  // derived values
  if (!projectId) return null;
  const projectDetails = getProjectById(projectId?.toString());
  if (!projectDetails) return null;

  return (
    <>
      {ARCHIVES_TAB_LIST.map(
        (tab) =>
          tab.shouldRender(projectDetails) && (
            <Link key={tab.key} href={`/${workspaceSlug}/projects/${projectId}/archives/${tab.key}`}>
              <span
                className={`flex min-w-min flex-shrink-0 border-b-2 px-4 py-4 text-13 font-medium whitespace-nowrap outline-none ${
                  pathname.includes(tab.key)
                    ? "border-accent-strong text-accent-primary"
                    : "border-transparent text-tertiary hover:border-subtle hover:text-placeholder"
                }`}
              >
                {t(tab.i18n_label)}
              </span>
            </Link>
          )
      )}
    </>
  );
});
