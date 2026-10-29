/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
// services
import { ProjectService } from "@/services/project/project.service";

const projectService = new ProjectService();

type Props = {
  workspaceSlug: string;
  projectId: string;
};

/** The open requests to join a Private project, for its admins to approve or reject. */
export const ProjectAccessRequests = observer(function ProjectAccessRequests(props: Props) {
  const { workspaceSlug, projectId } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [decidingId, setDecidingId] = useState<string | null>(null);
  // store hooks
  const { currentProjectDetails } = useProject();
  const {
    project: { fetchProjectMembers },
  } = useMember();

  const isPrivate = currentProjectDetails?.network === 1;
  const { data: requests, mutate } = useSWR(
    isPrivate ? `PROJECT_ACCESS_REQUESTS_${workspaceSlug}_${projectId}` : null,
    () => projectService.getProjectAccessRequests(workspaceSlug, projectId)
  );

  if (!isPrivate || !requests || requests.length === 0) return null;

  const decide = async (requestId: string, status: "approved" | "rejected") => {
    setDecidingId(requestId);
    try {
      await projectService.decideProjectAccessRequest(workspaceSlug, projectId, requestId, status);
      await mutate();
      // an approved person is a member now
      if (status === "approved") await fetchProjectMembers(workspaceSlug, projectId);
    } catch (error) {
      // 409: another admin decided first. 400: the requester left the workspace. Either way the
      // request is settled, so refresh the list instead of leaving it to be clicked again.
      const code = (error as { status?: number } | undefined)?.status;
      const messageKey =
        code === 409
          ? "project_components.access_requests.already_decided"
          : code === 400
            ? "project_components.access_requests.requester_left"
            : "something_went_wrong_please_try_again";
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t(messageKey),
      });
      if (code === 409 || code === 400) await mutate();
    } finally {
      setDecidingId(null);
    }
  };

  return (
    <section className="flex flex-col gap-2 border-b border-subtle pb-4">
      <h4 className="text-14 font-medium">
        {t("project_components.access_requests.title", { count: requests.length })}
      </h4>
      <ul className="flex flex-col gap-2">
        {requests.map((request) => (
          <li key={request.id} className="flex items-center justify-between gap-3 rounded-md border border-subtle p-2">
            <div className="min-w-0">
              <p className="truncate text-13 font-medium">
                {request.requester_detail.display_name || request.requester_detail.email}
              </p>
              {request.message && <p className="text-12 break-words text-tertiary">{request.message}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                stretch="auto"
                disabled={decidingId === request.id}
                label={t("project_components.access_requests.reject")}
                onClick={() => void decide(request.id, "rejected")}
              />
              <Button
                variant="primary"
                size="sm"
                stretch="auto"
                disabled={decidingId === request.id}
                label={t("project_components.access_requests.approve")}
                onClick={() => void decide(request.id, "approved")}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
});
