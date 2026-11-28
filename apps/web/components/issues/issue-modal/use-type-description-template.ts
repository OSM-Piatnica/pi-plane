/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
import { getDescriptionForTypeChange } from "@/helpers/work-item-type-template";
import { useProjectIssueTypes } from "@/hooks/use-project-issue-types";

type TParams = {
  /** Only a new work item takes a template: an existing description is never touched */
  enabled: boolean;
  workspaceSlug: string | undefined;
  projectId: string | null | undefined;
  typeId: string | null | undefined;
  getDescription: () => string | undefined;
  applyDescription: (html: string) => void;
};

/**
 * Put the description template of the chosen type into the description of a new work item while the description
 * is empty (or still holds the template of the type chosen before, unchanged). See `getDescriptionForTypeChange`.
 */
export function useTypeDescriptionTemplate(params: TParams) {
  const { enabled, workspaceSlug, projectId, typeId, getDescription, applyDescription } = params;
  const { types } = useProjectIssueTypes(workspaceSlug, enabled ? projectId : null);
  const template = types.find((row) => row.issue_type_id === typeId)?.issue_type_detail?.description_template ?? null;
  // the template this form put in last, to tell an untouched template from what a person wrote
  const lastApplied = useRef<string | null>(null);

  // The type also changes without an event of this form: the type select picks the project's default type in an
  // effect, and a work item template sets it
  useEffect(() => {
    if (!enabled) return;
    const next = getDescriptionForTypeChange({
      currentHtml: getDescription(),
      template,
      lastApplied: lastApplied.current,
    });
    if (next === undefined) return;
    // react-doctor-disable-next-line no-pass-data-to-parent -- the description belongs to the form, and the type changes without an event of the form (see above)
    applyDescription(next);
    lastApplied.current = template;
    // the callbacks are recreated on every render of the form; the template of the chosen type is what counts
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, typeId, template]);
}
