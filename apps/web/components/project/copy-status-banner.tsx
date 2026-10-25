/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the project duplication of Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import type { TProjectCopyJob } from "@plane/types";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { ProjectService } from "@/services/project/project.service";

const projectService = new ProjectService();

const POLL_MS = 3000;

const isActive = (job: TProjectCopyJob | null | undefined) => job?.status === "queued" || job?.status === "processing";

type Props = {
  workspaceSlug: string;
  projectId: string;
};

/**
 * Shows how far the background copy of a duplicated project's work items has got, and offers a retry
 * when it failed. Renders nothing for a project that was never copied, or whose copy finished before
 * this page was opened.
 */
export const ProjectCopyStatusBanner = observer(function ProjectCopyStatusBanner(props: Props) {
  const { workspaceSlug, projectId } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const { allowPermissions } = useUserPermissions();
  // states
  const [isRetrying, setIsRetrying] = useState(false);
  // A copy that is seen running is announced when it ends; one that ended long ago is not
  const watched = useRef(false);

  const { data: job, mutate } = useSWR(
    `PROJECT_COPY_STATUS_${workspaceSlug}_${projectId}`,
    () => projectService.getProjectCopyStatus(workspaceSlug, projectId),
    // polls only while there is something to wait for
    {
      refreshInterval: (latest) => (isActive(latest) ? POLL_MS : 0),
      shouldRetryOnError: false,
      onSuccess: (latest) => {
        if (isActive(latest)) watched.current = true;
      },
    }
  );

  const active = isActive(job);

  const canRetry = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  const retry = async () => {
    setIsRetrying(true);
    try {
      await mutate(projectService.retryProjectCopy(workspaceSlug, projectId), { revalidate: false });
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("project_components.duplicate_modal.banner.retry_failed"),
      });
    } finally {
      setIsRetrying(false);
    }
  };

  if (!job) return null;

  if (active) {
    const percent = job.total > 0 ? Math.min(100, Math.round((job.copied / job.total) * 100)) : 0;
    return (
      <div role="status" className="flex shrink-0 flex-col gap-1.5 border-b border-subtle bg-layer-1 px-page-x py-2">
        <p className="text-13 text-secondary">
          {job.status === "queued"
            ? t("project_components.duplicate_modal.banner.queued")
            : t("project_components.duplicate_modal.banner.progress", { copied: job.copied, total: job.total })}
        </p>
        <div className="h-1 w-full overflow-hidden rounded-full bg-layer-3">
          <div className="h-full bg-accent-primary transition-all" style={{ width: `${percent}%` }} />
        </div>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div
        role="alert"
        className="flex shrink-0 items-center justify-between gap-3 border-b border-subtle bg-danger-subtle px-page-x py-2"
      >
        <p className="text-13 text-danger-primary">{t("project_components.duplicate_modal.banner.failed")}</p>
        {canRetry && (
          <Button
            variant="secondary"
            size="sm"
            stretch="auto"
            loading={isRetrying}
            label={t("project_components.duplicate_modal.banner.retry")}
            onClick={() => void retry()}
          />
        )}
      </div>
    );
  }

  if (watched.current && (job.status === "completed" || job.status === "completed_with_errors")) {
    return (
      <div
        role="status"
        className="flex shrink-0 items-center justify-between gap-3 border-b border-subtle bg-layer-1 px-page-x py-2"
      >
        <p className="text-13 text-secondary">
          {t("project_components.duplicate_modal.banner.done", { count: job.copied })}
        </p>
        <Button
          variant="secondary"
          size="sm"
          stretch="auto"
          label={t("project_components.duplicate_modal.banner.reload")}
          onClick={() => window.location.reload()}
        />
      </div>
    );
  }

  return null;
});
