import React, { useCallback, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { DEFAULT_WORK_ITEM_FORM_VALUES } from "@plane/constants";
import type { ISearchIssueResponse, TIssue } from "@plane/types";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { useTranslation } from "@plane/i18n";
import { IssueModalContext } from "@/components/issues/issue-modal/context";
import { useUser } from "@/hooks/store/user/user-user";
import { WorkItemTemplateService } from "@/services/work-item-template.service";

const workItemTemplateService = new WorkItemTemplateService();

export type TIssueModalProviderProps = {
  templateId?: string;
  dataForPreload?: Partial<TIssue>;
  allowedProjectIds?: string[];
  children: React.ReactNode;
};

export const IssueModalProvider = observer(function IssueModalProvider(props: TIssueModalProviderProps) {
  const { children, allowedProjectIds } = props;
  const { t } = useTranslation();
  const [workItemTemplateId, setWorkItemTemplateId] = useState<string | null>(null);
  const [isApplyingTemplate, setIsApplyingTemplate] = useState(false);
  const [selectedParentIssue, setSelectedParentIssue] = useState<ISearchIssueResponse | null>(null);
  const { projectsWithCreatePermissions } = useUser();
  const projectIdsWithCreatePermissions = Object.keys(projectsWithCreatePermissions ?? {});

  const handleTemplateChange = useCallback(
    async (propsArg: {
      workspaceSlug: string;
      projectId: string;
      templateId: string | null;
      reset: (values: Partial<TIssue>) => void;
      editorRef: React.MutableRefObject<import("@plane/editor").EditorRefApi | null>;
    }) => {
      const { workspaceSlug: slug, projectId, templateId, reset, editorRef } = propsArg;
      if (!templateId) return;
      if (!projectId) return;
      setIsApplyingTemplate(true);
      try {
        const data = await workItemTemplateService.retrieve(slug, templateId, projectId);
        const payload = data.resolved_payload ?? data.payload ?? {};
        const descriptionHtml =
          payload.description_html && payload.description_html !== "" ? String(payload.description_html) : "<p></p>";
        reset({
          ...DEFAULT_WORK_ITEM_FORM_VALUES,
          project_id: projectId,
          name: payload.name != null && String(payload.name) !== "" ? String(payload.name) : "",
          description_html: descriptionHtml,
          type_id: payload.type_id ?? null,
          state_id: payload.state_id ?? "",
          priority: payload.priority ?? "none",
          label_ids: Array.isArray(payload.label_ids) ? payload.label_ids : [],
          assignee_ids: Array.isArray(payload.assignee_ids) ? payload.assignee_ids : [],
          estimate_point: payload.estimate_point ?? null,
          cycle_id: payload.cycle_id ?? null,
          module_ids: Array.isArray(payload.module_ids) && payload.module_ids.length > 0 ? payload.module_ids : null,
          start_date: payload.start_date ?? null,
          target_date: payload.target_date ?? null,
          parent_id: null,
        });
        const applyEditor = () => editorRef.current?.setEditorValue?.(descriptionHtml, false);
        requestAnimationFrame(applyEditor);
        setTimeout(applyEditor, 0);
        setTimeout(applyEditor, 50);
      } catch (e) {
        console.error(e);
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("error"),
          message: t("work_item_templates.apply_failed_toast"),
        });
        setWorkItemTemplateId(null);
      } finally {
        setIsApplyingTemplate(false);
      }
    },
    [t]
  );

  const contextValue = useMemo(
    () => ({
      allowedProjectIds: allowedProjectIds ?? projectIdsWithCreatePermissions,
      workItemTemplateId,
      setWorkItemTemplateId,
      isApplyingTemplate,
      setIsApplyingTemplate,
      selectedParentIssue,
      setSelectedParentIssue,
      issuePropertyValues: {},
      setIssuePropertyValues: () => {},
      issuePropertyValueErrors: {},
      setIssuePropertyValueErrors: () => {},
      getIssueTypeIdOnProjectChange: () => null,
      getActiveAdditionalPropertiesLength: () => 0,
      handlePropertyValuesValidation: () => true,
      handleCreateUpdatePropertyValues: () => Promise.resolve(),
      handleProjectEntitiesFetch: () => Promise.resolve(),
      handleTemplateChange,
      handleConvert: () => Promise.resolve(),
      handleCreateSubWorkItem: () => Promise.resolve(),
    }),
    [
      allowedProjectIds,
      handleTemplateChange,
      isApplyingTemplate,
      projectIdsWithCreatePermissions,
      selectedParentIssue,
      workItemTemplateId,
    ]
  );

  return <IssueModalContext.Provider value={contextValue}>{children}</IssueModalContext.Provider>;
});
