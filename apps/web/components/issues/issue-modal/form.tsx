/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useState, useRef, useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { FormProvider, useForm } from "react-hook-form";
// editor
import { ETabIndices, DEFAULT_WORK_ITEM_FORM_VALUES } from "@plane/constants";
import type { EditorRefApi } from "@plane/editor";
// i18n
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  DialogActions,
  DialogBody,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { setToast } from "@plane/blocks/toast";
import type { TIssue, TWorkspaceDraftIssue } from "@plane/types";
// hooks
import { Switch } from "@makeplane/propel/components/switch";
import {
  convertWorkItemDataToSearchResponse,
  getUpdateFormDataForReset,
  getTextContent,
  getChangedIssuefields,
  getTabIndex,
} from "@plane/utils";
// components
import {
  IssueDefaultProperties,
  IssueDescriptionEditor,
  IssueParentTag,
  IssueProjectSelect,
  IssueTitleInput,
} from "@/components/issues/issue-modal/components";
// helpers
// hooks
import { useIssueModal } from "@/hooks/context/use-issue-modal";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useWorkspaceDraftIssues } from "@/hooks/store/workspace-draft";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useReportFormInput } from "@/hooks/use-report-form-input";
import { useProjectIssueProperties } from "@/hooks/use-project-issue-properties";
import { DeDupeButtonRoot } from "@/components/de-dupe/de-dupe-button";
import { DuplicateModalRoot } from "@/components/de-dupe/duplicate-modal";
import { IssueTypeSelect, WorkItemTemplateSelect } from "@/components/issues/issue-modal";
import { WorkItemModalAdditionalProperties } from "@/components/issues/issue-modal/modal-additional-properties";
import { useDebouncedDuplicateIssues } from "@/hooks/use-debounced-duplicate-issues";

export interface IssueFormProps {
  data?: Partial<TIssue>;
  issueTitleRef: React.MutableRefObject<HTMLInputElement | null>;
  isCreateMoreToggleEnabled: boolean;
  onAssetUpload: (assetId: string) => void;
  onCreateMoreToggleChange: (value: boolean) => void;
  onChange?: (formData: Partial<TIssue> | null) => void;
  /** Reports whether the form holds anything the user entered, so the dialog can ignore outside clicks then. */
  onInputChange?: (hasInput: boolean) => void;
  onClose: () => void;
  onSubmit: (values: Partial<TIssue>, is_draft_issue?: boolean) => Promise<void>;
  projectId: string;
  isDraft: boolean;
  moveToIssue?: boolean;
  modalTitle?: string;
  primaryButtonText?: {
    default: string;
    loading: string;
  };
  isDuplicateModalOpen: boolean;
  handleDuplicateIssueModal: (isOpen: boolean) => void;
  handleDraftAndClose?: () => void;
  isProjectSelectionDisabled?: boolean;
  showActionButtons?: boolean;
  dataResetProperties?: any[];
}

export const IssueFormRoot = observer(function IssueFormRoot(props: IssueFormProps) {
  const { t } = useTranslation();
  const {
    data,
    issueTitleRef,
    onAssetUpload,
    onChange,
    onInputChange,
    onClose,
    onSubmit,
    projectId: defaultProjectId,
    isCreateMoreToggleEnabled,
    onCreateMoreToggleChange,
    isDraft,
    moveToIssue = false,
    modalTitle = `${data?.id ? t("update") : isDraft ? t("create_a_draft") : t("create_new_issue")}`,
    primaryButtonText = {
      default: `${data?.id ? t("update") : isDraft ? t("save_to_drafts") : t("save")}`,
      loading: `${data?.id ? t("updating") : t("saving")}`,
    },
    isDuplicateModalOpen,
    handleDuplicateIssueModal,
    handleDraftAndClose,
    isProjectSelectionDisabled = false,
    showActionButtons = true,
    dataResetProperties = [],
  } = props;

  // states
  const [gptAssistantModal, setGptAssistantModal] = useState(false);
  const [isMoving, setIsMoving] = useState<boolean>(false);

  // refs
  const editorRef = useRef<EditorRefApi>(null);
  const submitBtnRef = useRef<HTMLButtonElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const modalContainerRef = useRef<HTMLDivElement | null>(null);

  // router
  const { workspaceSlug, projectId: routeProjectId } = useParams();

  // store hooks
  const { getProjectById } = useProject();
  const {
    workItemTemplateId,
    isApplyingTemplate,
    selectedParentIssue,
    setWorkItemTemplateId,
    setSelectedParentIssue,
    getIssueTypeIdOnProjectChange,
    handlePropertyValuesValidation,
    handleCreateUpdatePropertyValues,
    handleTemplateChange,
  } = useIssueModal();
  const { isMobile } = usePlatformOS();
  const { moveIssue } = useWorkspaceDraftIssues();

  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { fetchCycles } = useProjectIssueProperties();
  const { getStateById } = useProjectState();

  // form info
  const methods = useForm<TIssue>({
    defaultValues: { ...DEFAULT_WORK_ITEM_FORM_VALUES, project_id: defaultProjectId, ...data },
    reValidateMode: "onChange",
  });
  const {
    formState,
    formState: { isDirty, isSubmitting, dirtyFields },
    handleSubmit,
    reset,
    watch,
    control,
    getValues,
    setValue,
  } = methods;

  const projectId = watch("project_id");
  /** Wartość z RHF, żeby `value` w RichText odpowiadała resetowi i szablonowi (przy create `data` nie ma `description_html`). */
  const descriptionHtmlForEditor = watch("description_html");

  // derived values
  const projectDetails = projectId ? getProjectById(projectId) : undefined;
  const isDisabled = isSubmitting || isApplyingTemplate;

  const { getIndex } = getTabIndex(ETabIndices.ISSUE_FORM, isMobile);

  useReportFormInput(isDirty, onInputChange);

  //reset few fields on projectId change
  useEffect(() => {
    if (isDirty) {
      if (workItemTemplateId) {
        // reset work item template id
        setWorkItemTemplateId(null);
        reset({ ...DEFAULT_WORK_ITEM_FORM_VALUES, project_id: projectId });
        editorRef.current?.clearEditor();
      } else {
        reset(getUpdateFormDataForReset(projectId, getValues()));
      }
    }
    if (projectId && routeProjectId !== projectId) fetchCycles(workspaceSlug?.toString(), projectId);

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Reset form when issue data loads (e.g. description_html after fetchIssueDetail)
  useEffect(() => {
    if (data) {
      reset({ ...DEFAULT_WORK_ITEM_FORM_VALUES, project_id: projectId, ...data });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.id, data?.description_html, projectId, ...dataResetProperties]);

  // Update the issue type id when the project id changes
  useEffect(() => {
    const issueTypeId = watch("type_id");

    // if issue type id is present or project not available, return
    if (issueTypeId || !projectId) return;

    // get issue type id on project change
    const issueTypeIdOnProjectChange = getIssueTypeIdOnProjectChange(projectId);
    if (issueTypeIdOnProjectChange) setValue("type_id", issueTypeIdOnProjectChange, { shouldValidate: true });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, projectId]);

  useEffect(() => {
    if (workItemTemplateId && projectId) {
      handleTemplateChange({
        workspaceSlug: workspaceSlug?.toString() ?? "",
        projectId,
        templateId: workItemTemplateId,
        reset,
        editorRef,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workItemTemplateId, projectId]);

  const handleFormSubmit = async (formData: Partial<TIssue>, is_draft_issue = false) => {
    // Check if the editor is ready to discard
    if (!editorRef.current?.isEditorReadyToDiscard()) {
      setToast({
        type: "error",
        title: t("error"),
        message: t("editor_is_not_ready_to_discard_changes"),
      });
      return;
    }

    // check for required properties validation
    if (
      !handlePropertyValuesValidation({
        projectId: projectId,
        workspaceSlug: workspaceSlug?.toString(),
        watch: watch,
      })
    )
      return;

    const submitData = !data?.id
      ? { ...formData, type_id: formData.type_id ?? getValues("type_id") }
      : {
          ...getChangedIssuefields(formData, dirtyFields as { [key: string]: boolean | undefined }),
          project_id: getValues<"project_id">("project_id"),
          id: data.id,
          description_html: formData.description_html ?? "<p></p>",
          type_id: getValues<"type_id">("type_id"),
        };

    // this condition helps to move the issues from draft to project issues
    if (formData.hasOwnProperty("is_draft")) submitData.is_draft = formData.is_draft;

    await onSubmit(submitData, is_draft_issue)
      .then(() => {
        setGptAssistantModal(false);
        if (isCreateMoreToggleEnabled && workItemTemplateId && projectId) {
          handleTemplateChange({
            workspaceSlug: workspaceSlug?.toString() ?? "",
            projectId,
            templateId: workItemTemplateId,
            reset,
            editorRef,
          });
        } else {
          reset({
            ...DEFAULT_WORK_ITEM_FORM_VALUES,
            ...(isCreateMoreToggleEnabled ? { ...data } : {}),
            project_id: getValues<"project_id">("project_id"),
            type_id: getValues<"type_id">("type_id"),
            description_html: data?.description_html ?? "<p></p>",
          });
          editorRef?.current?.clearEditor();
        }
        return;
      })
      .catch((error) => {
        console.error(error);
      });
  };

  const handleMoveToProjects = async () => {
    if (!data?.id || !data?.project_id || !data) return;
    setIsMoving(true);
    try {
      await handleCreateUpdatePropertyValues({
        issueId: data.id,
        issueTypeId: data.type_id,
        projectId: data.project_id,
        workspaceSlug: workspaceSlug?.toString(),
        isDraft: true,
      });

      await moveIssue(workspaceSlug.toString(), data.id, {
        ...data,
        ...getValues(),
      } as TWorkspaceDraftIssue);
    } catch {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("issue_ui.move_to_project_failed"),
      });
    } finally {
      setIsMoving(false);
    }
  };

  const condition =
    (watch("name") && watch("name") !== "") || (watch("description_html") && watch("description_html") !== "<p></p>");

  const handleFormChange = () => {
    if (!onChange) return;

    if (isDirty && condition) onChange(watch());
    else onChange(null);
  };

  // debounced duplicate issues swr
  const { duplicateIssues } = useDebouncedDuplicateIssues(
    workspaceSlug?.toString(),
    projectDetails?.workspace.toString(),
    projectId ?? undefined,
    {
      name: watch("name"),
      description_html: getTextContent(watch("description_html")),
      issueId: data?.id,
    }
  );

  // executing this useEffect when the parent_id coming from the component prop
  useEffect(() => {
    const parentId = watch("parent_id") || undefined;
    if (!parentId) return;
    if (parentId === selectedParentIssue?.id || selectedParentIssue) return;

    const issue = getIssueById(parentId);
    if (!issue) return;

    const parentProjectDetails = getProjectById(issue.project_id);
    if (!parentProjectDetails) return;

    const stateDetails = getStateById(issue.state_id);

    setSelectedParentIssue(
      convertWorkItemDataToSearchResponse(workspaceSlug?.toString(), issue, parentProjectDetails, stateDetails)
    );
    // oxlint-disable-next-line eslint-plugin-react-hooks/exhaustive-deps
  }, [watch, getIssueById, getProjectById, selectedParentIssue, getStateById]);

  // executing this useEffect when isDirty changes
  useEffect(() => {
    if (!onChange) return;

    if (isDirty && condition) onChange(watch());
    else onChange(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDirty]);

  useEffect(() => {
    const formElement = formRef?.current;
    const modalElement = modalContainerRef?.current;

    if (!formElement || !modalElement) return;

    const resizeObserver = new ResizeObserver(() => {
      modalElement.style.maxHeight = `${formElement?.offsetHeight}px`;
    });

    resizeObserver.observe(formElement);

    return () => {
      resizeObserver.disconnect();
    };
  }, [formRef, modalContainerRef]);

  // TODO: Remove this after the de-dupe feature is implemented

  const shouldRenderDuplicateModal = isDuplicateModalOpen && duplicateIssues?.length > 0;

  return (
    <FormProvider {...methods}>
      {/* The form relays DialogContent's max-height into Main/Body: the description scrolls in
          DialogBody, default properties stay pinned in Main and buttons live in DialogActions. When the window is
          too short for the header, a usable body and the buttons together, DialogBody keeps a minimum height
          (instead of shrinking to nothing) and this wrapper scrolls the whole form. */}
      <div className="vertical-scrollbar scrollbar-sm flex min-h-0 flex-1 gap-2 overflow-y-auto bg-transparent">
        <form
          ref={formRef}
          onSubmit={handleSubmit((formValues) => handleFormSubmit(formValues))}
          className="flex min-h-0 w-full flex-1 flex-col"
        >
          {/* DialogMain clips its content and shrinks to the form; letting it grow to its content makes the wrapper
              above scroll instead of cutting the header, body and buttons off in a short window. */}
          <DialogMain render={<div style={{ minHeight: "min-content", overflow: "visible" }} />}>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>{modalTitle}</DialogTitle>
              </DialogHeading>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-x-1">
                  <IssueProjectSelect
                    control={control}
                    disabled={!!data?.id || !!data?.sourceIssueId || isProjectSelectionDisabled}
                    handleFormChange={handleFormChange}
                  />
                  {projectId && (
                    <IssueTypeSelect
                      control={control}
                      projectId={projectId}
                      editorRef={editorRef}
                      disabled={!!data?.sourceIssueId}
                      handleFormChange={handleFormChange}
                      renderChevron
                    />
                  )}
                  {projectId && !data?.id && !data?.sourceIssueId && (
                    <WorkItemTemplateSelect
                      projectId={projectId}
                      typeId={watch("type_id")}
                      handleModalClose={() => {
                        if (handleDraftAndClose) {
                          handleDraftAndClose();
                        } else {
                          onClose();
                        }
                      }}
                      handleFormChange={handleFormChange}
                      renderChevron
                    />
                  )}
                </div>
                {duplicateIssues.length > 0 && (
                  <DeDupeButtonRoot
                    workspaceSlug={workspaceSlug?.toString()}
                    isDuplicateModalOpen={isDuplicateModalOpen}
                    label={
                      duplicateIssues.length === 1
                        ? `${duplicateIssues.length} ${t("duplicate_issue_found")}`
                        : `${duplicateIssues.length} ${t("duplicate_issues_found")}`
                    }
                    handleOnClick={() => handleDuplicateIssueModal(!isDuplicateModalOpen)}
                  />
                )}
              </div>
              {watch("parent_id") && selectedParentIssue && (
                <IssueParentTag
                  control={control}
                  selectedParentIssue={selectedParentIssue}
                  handleFormChange={handleFormChange}
                  setSelectedParentIssue={setSelectedParentIssue}
                />
              )}
              <IssueTitleInput
                control={control}
                issueTitleRef={issueTitleRef}
                formState={formState}
                handleFormChange={handleFormChange}
              />
            </DialogHeader>
            <DialogBody
              tabIndex={0}
              render={<div className="vertical-scrollbar scrollbar-sm" style={{ minHeight: "10rem" }} />}
            >
              <IssueDescriptionEditor
                control={control}
                isDraft={isDraft}
                issueName={watch("name")}
                issueId={data?.id}
                descriptionHtmlData={descriptionHtmlForEditor}
                editorRef={editorRef}
                submitBtnRef={submitBtnRef}
                gptAssistantModal={gptAssistantModal}
                workspaceSlug={workspaceSlug?.toString()}
                projectId={projectId}
                handleFormChange={handleFormChange}
                handleDescriptionHTMLDataChange={(description_html) =>
                  setValue<"description_html">("description_html", description_html)
                }
                setGptAssistantModal={setGptAssistantModal}
                handleGptAssistantClose={() => reset(getValues())}
                onAssetUpload={onAssetUpload}
                onClose={onClose}
              />
              <WorkItemModalAdditionalProperties
                isDraft={isDraft}
                workItemId={data?.id ?? data?.sourceIssueId}
                projectId={projectId}
                workspaceSlug={workspaceSlug?.toString()}
              />
            </DialogBody>
            <div className="shrink-0">
              <IssueDefaultProperties
                control={control}
                id={data?.id}
                projectId={projectId}
                workspaceSlug={workspaceSlug?.toString()}
                selectedParentIssue={selectedParentIssue}
                getValues={getValues}
                setValue={setValue}
                parentId={watch("parent_id")}
                isDraft={isDraft}
                handleFormChange={handleFormChange}
                setSelectedParentIssue={setSelectedParentIssue}
              />
            </div>
          </DialogMain>
          {showActionButtons && (
            <DialogActions>
              {!data?.id && (
                <label className="inline-flex cursor-pointer items-center gap-1.5" tabIndex={getIndex("create_more")}>
                  <Switch
                    size="sm"
                    checked={isCreateMoreToggleEnabled}
                    onCheckedChange={(checked) => onCreateMoreToggleChange(checked)}
                    aria-label={t("create_more")}
                  />
                  <span className="text-caption-sm-regular">{t("create_more")}</span>
                </label>
              )}
              <div tabIndex={getIndex("discard_button")}>
                <Button
                  variant="secondary"
                  size="md"
                  stretch="auto"
                  onClick={() => {
                    if (editorRef.current?.isEditorReadyToDiscard()) {
                      onClose();
                    } else {
                      setToast({
                        type: "error",
                        title: t("toast.error"),
                        message: t("issue_ui.editor_processing"),
                      });
                    }
                  }}
                  label={t("discard")}
                />
              </div>
              <div tabIndex={isDraft ? getIndex("submit_button") : getIndex("draft_button")}>
                <Button
                  variant={moveToIssue ? "secondary" : "primary"}
                  size="md"
                  stretch="auto"
                  type="submit"
                  ref={submitBtnRef}
                  loading={isSubmitting}
                  disabled={isDisabled}
                  label={isSubmitting ? primaryButtonText.loading : primaryButtonText.default}
                />
              </div>
              {moveToIssue && (
                <Button
                  variant="primary"
                  type="button"
                  loading={isMoving}
                  onClick={handleMoveToProjects}
                  disabled={isMoving}
                  size="md"
                  stretch="auto"
                  label={t("add_to_project")}
                />
              )}
            </DialogActions>
          )}
        </form>
        {shouldRenderDuplicateModal && (
          <div
            ref={modalContainerRef}
            className="shadow-xl bg-pi-50 relative flex flex-col gap-2.5 rounded-lg px-3 py-4"
            style={{ maxHeight: formRef?.current?.offsetHeight ? `${formRef.current.offsetHeight}px` : "436px" }}
          >
            <DuplicateModalRoot
              workspaceSlug={workspaceSlug.toString()}
              issues={duplicateIssues}
              handleDuplicateIssueModal={handleDuplicateIssueModal}
            />
          </div>
        )}
      </div>
    </FormProvider>
  );
});
