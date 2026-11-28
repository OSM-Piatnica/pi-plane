/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { RichTextEditor } from "@/components/editor/rich-text";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { WorkspaceService } from "@/services/workspace.service";

const workspaceService = new WorkspaceService();

type Props = {
  /** Remounts the editor when another type is opened in the form */
  editorKey: string;
  workspaceSlug: string;
  value: string;
  onChange: (html: string) => void;
};

/**
 * The description template of a work item type. Images are off: a template is copied into many work items, and an
 * uploaded file belongs to one of them.
 */
export const WorkItemTypeTemplateEditor = observer(function WorkItemTypeTemplateEditor(props: Props) {
  const { editorKey, workspaceSlug, value, onChange } = props;
  const { t } = useTranslation();
  const { getWorkspaceBySlug } = useWorkspace();
  const workspaceId = getWorkspaceBySlug(workspaceSlug)?.id ?? "";

  return (
    <div className="rounded-md border border-subtle bg-layer-2">
      <RichTextEditor
        key={editorKey}
        editable
        id={`work-item-type-template-${editorKey}`}
        initialValue={value || "<p></p>"}
        workspaceSlug={workspaceSlug}
        workspaceId={workspaceId}
        disabledExtensions={["image"]}
        onChange={(_json: object, html: string) => onChange(html)}
        placeholder={t("workspace_settings.settings.work_item_types.form.description_template_placeholder")}
        searchMentionCallback={async (payload) => await workspaceService.searchEntity(workspaceSlug, payload)}
        uploadFile={async () => {
          throw new Error("Images are not supported in a description template");
        }}
        duplicateFile={async () => {
          throw new Error("Images are not supported in a description template");
        }}
        containerClassName="min-h-[120px] pt-3"
      />
    </div>
  );
});
