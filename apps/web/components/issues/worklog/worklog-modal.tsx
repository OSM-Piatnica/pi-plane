/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Pencil, Trash2 } from "lucide-react";
// plane imports
import { EUserPermissions } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogCloseGroup,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { CloseOutline } from "@makeplane/propel/icons";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import type { TIssueWorklog } from "@plane/types";
import { renderFormattedDate } from "@plane/utils";
// helpers
import { MAX_WORKLOG_DESCRIPTION_LENGTH, formatWorklogDuration, parseLoggableWorklogDuration } from "@/helpers/worklog";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useWorklogs } from "@/hooks/use-worklogs";
// services
import { worklogService } from "@/services/issue/worklog.service";

type TWorklogModal = {
  isOpen: boolean;
  onClose: () => void;
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
};

/** The time logged on a work item: add an entry, and change or delete your own (an admin: any). */
export const WorklogModal = observer(function WorklogModal(props: TWorklogModal) {
  const { isOpen, onClose, workspaceSlug, projectId, issueId, disabled = false } = props;
  const { t } = useTranslation();
  // adding
  const [durationInput, setDurationInput] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  // changing
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDurationInput, setEditDurationInput] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  // store hooks
  const { data: currentUser } = useUser();
  const { getUserDetails } = useMember();
  const { getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  const { fetchActivities } = useIssueDetail();
  // derived values
  const { worklogs, totalDuration, isLoading, mutate } = useWorklogs(workspaceSlug, projectId, issueId, isOpen);
  const isAdmin = getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId) === EUserPermissions.ADMIN;
  const canModify = (worklog: TIssueWorklog) => !disabled && (isAdmin || worklog.logged_by === currentUser?.id);

  // also refreshes the activity feed, which shows the entry
  const refresh = async () => {
    await mutate();
    fetchActivities(workspaceSlug, projectId, issueId, "mutate").catch(() => undefined);
  };

  const handleClose = () => {
    setDurationInput("");
    setDescription("");
    setEditingId(null);
    setPendingDeleteId(null);
    onClose();
  };

  const showInvalidDuration = () =>
    setToast({
      type: "error",
      title: t("worklog.invalid_duration_title"),
      message: t("worklog.invalid_duration_message"),
    });

  const run = async (action: () => Promise<void>, failure: string) => {
    setIsSubmitting(true);
    try {
      await action();
      await refresh();
    } catch (error) {
      console.error(error);
      setToast({ type: "error", title: t("toast.error"), message: failure });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreate = async () => {
    const minutes = parseLoggableWorklogDuration(durationInput);
    if (minutes === null) return showInvalidDuration();
    await run(async () => {
      await worklogService.createWorklog(workspaceSlug, projectId, issueId, {
        duration: minutes,
        description: description.trim(),
      });
      setDurationInput("");
      setDescription("");
    }, t("worklog.log_error"));
  };

  const startEditing = (worklog: TIssueWorklog) => {
    setEditingId(worklog.id);
    setEditDurationInput(formatWorklogDuration(worklog.duration));
    setEditDescription(worklog.description ?? "");
  };

  const handleUpdate = async (worklogId: string) => {
    const minutes = parseLoggableWorklogDuration(editDurationInput);
    if (minutes === null) return showInvalidDuration();
    await run(async () => {
      await worklogService.updateWorklog(workspaceSlug, projectId, issueId, worklogId, {
        duration: minutes,
        description: editDescription.trim(),
      });
      setEditingId(null);
    }, t("worklog.update_error"));
  };

  const handleDelete = async (worklogId: string) => {
    await run(async () => {
      await worklogService.deleteWorklog(workspaceSlug, projectId, issueId, worklogId);
      setPendingDeleteId(null);
    }, t("worklog.delete_error"));
  };

  return (
    <>
      <ConfirmDialog
        isOpen={pendingDeleteId !== null}
        handleClose={() => setPendingDeleteId(null)}
        handleSubmit={() => (pendingDeleteId ? handleDelete(pendingDeleteId) : undefined)}
        isSubmitting={isSubmitting}
        title={t("worklog.delete_title")}
        content={<>{t("worklog.delete_description")}</>}
      />
      <Dialog
        open={isOpen}
        onOpenChange={(open) => {
          if (!open) handleClose();
        }}
      >
        <DialogContent size="lg">
          <DialogCloseGroup>
            <IconButton
              variant="ghost"
              size="xs"
              aria-label={t("close")}
              icon={<Icon icon={CloseOutline} />}
              render={<DialogClose />}
            />
          </DialogCloseGroup>
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{t("time_tracking")}</DialogTitle>
              </DialogHeading>
              <span className="text-body-xs-regular text-tertiary">
                {t("common.worklogs")}:{" "}
                <span className="text-body-xs-medium text-primary">{formatWorklogDuration(totalDuration)}</span>
              </span>
            </DialogHeader>
            <DialogBody tabIndex={0}>
              <div className="space-y-4">
                {!disabled && (
                  <div className="flex items-start gap-2">
                    <div className="w-28 shrink-0">
                      <InputGroup size="md">
                        <Input
                          size="md"
                          value={durationInput}
                          onChange={(event) => setDurationInput(event.target.value)}
                          placeholder="2h 30m"
                          aria-label={t("common.duration")}
                        />
                      </InputGroup>
                    </div>
                    <div className="min-w-0 grow">
                      <InputGroup size="md">
                        <Input
                          size="md"
                          value={description}
                          onChange={(event) => setDescription(event.target.value)}
                          placeholder={t("worklog.description_placeholder")}
                          aria-label={t("common.description")}
                          maxLength={MAX_WORKLOG_DESCRIPTION_LENGTH}
                        />
                      </InputGroup>
                    </div>
                    <Button
                      variant="primary"
                      size="md"
                      stretch="auto"
                      onClick={() => void handleCreate()}
                      loading={isSubmitting}
                      label={t("worklog.log_time")}
                    />
                  </div>
                )}

                <div className="max-h-72 space-y-1 overflow-y-auto">
                  {!isLoading && worklogs.length === 0 && (
                    <p className="py-4 text-center text-body-xs-regular text-tertiary">
                      {t("activity_empty_state.no_worklogs")}
                    </p>
                  )}
                  {worklogs.map((worklog) => {
                    const author = worklog.logged_by ? getUserDetails(worklog.logged_by) : undefined;
                    const isEditing = editingId === worklog.id;
                    return (
                      <div
                        key={worklog.id}
                        className="group flex items-center gap-2 rounded-md border border-subtle px-3 py-2 text-body-xs-regular"
                      >
                        {isEditing ? (
                          <>
                            <div className="w-28 shrink-0">
                              <InputGroup size="md">
                                <Input
                                  size="md"
                                  value={editDurationInput}
                                  onChange={(event) => setEditDurationInput(event.target.value)}
                                  placeholder="2h 30m"
                                  aria-label={t("common.duration")}
                                />
                              </InputGroup>
                            </div>
                            <div className="min-w-0 grow">
                              <InputGroup size="md">
                                <Input
                                  size="md"
                                  value={editDescription}
                                  onChange={(event) => setEditDescription(event.target.value)}
                                  placeholder={t("worklog.description_placeholder")}
                                  aria-label={t("common.description")}
                                  maxLength={MAX_WORKLOG_DESCRIPTION_LENGTH}
                                />
                              </InputGroup>
                            </div>
                            <Button
                              variant="primary"
                              size="sm"
                              stretch="auto"
                              onClick={() => void handleUpdate(worklog.id)}
                              loading={isSubmitting}
                              label={t("save")}
                            />
                            <Button
                              variant="secondary"
                              size="sm"
                              stretch="auto"
                              onClick={() => setEditingId(null)}
                              disabled={isSubmitting}
                              label={t("cancel")}
                            />
                          </>
                        ) : (
                          <>
                            <span className="w-20 shrink-0 text-body-xs-medium text-primary">
                              {formatWorklogDuration(worklog.duration)}
                            </span>
                            <span className="grow truncate text-secondary">{worklog.description}</span>
                            <span className="shrink-0 text-caption-sm-regular text-tertiary">
                              {author?.display_name ?? "—"} · {renderFormattedDate(worklog.created_at)}
                            </span>
                            {canModify(worklog) && (
                              <span className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
                                <button
                                  type="button"
                                  onClick={() => startEditing(worklog)}
                                  disabled={isSubmitting}
                                  className="rounded-sm p-1 text-tertiary hover:bg-layer-1 hover:text-primary"
                                  aria-label={t("worklog.edit_entry")}
                                >
                                  <Pencil className="size-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setPendingDeleteId(worklog.id)}
                                  disabled={isSubmitting}
                                  className="rounded-sm p-1 text-tertiary hover:bg-layer-1 hover:text-danger-primary"
                                  aria-label={t("worklog.delete_entry")}
                                >
                                  <Trash2 className="size-3.5" />
                                </button>
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </DialogBody>
          </DialogMain>
        </DialogContent>
      </Dialog>
    </>
  );
});
