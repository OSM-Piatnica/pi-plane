/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import type { TIssueRelationTypes, TIssueServiceType } from "@plane/types";
import { EIssueServiceType } from "@plane/types";
import { MAX_RELATION_LAG_DAYS, TIMELINE_RELATION_TYPES } from "@plane/utils";
// helpers
import { getIssueApiErrorMessage } from "@/helpers/issue-api-error";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  relationKey: TIssueRelationTypes;
  relatedIssueId: string;
  disabled: boolean;
  issueServiceType?: TIssueServiceType;
};

/** The relations whose dates can be kept apart (or overlapped) by a number of days. */
export const isLagRelation = (relationKey: TIssueRelationTypes) =>
  (TIMELINE_RELATION_TYPES as string[]).includes(relationKey);

type TInputProps = Props & { lag: number };

/**
 * The field itself. It is keyed on the stored lag by its parent, so it starts again from the stored value when that
 * changes from elsewhere or when a change is refused, without an effect resetting its state.
 */
const RelationLagInput = observer(function RelationLagInput(props: TInputProps) {
  const {
    workspaceSlug,
    projectId,
    issueId,
    relationKey,
    relatedIssueId,
    disabled,
    lag,
    issueServiceType = EIssueServiceType.ISSUES,
  } = props;
  const { t } = useTranslation();
  const {
    relation: { updateRelationLag },
  } = useIssueDetail(issueServiceType);
  const [draft, setDraft] = useState(String(lag));

  const commit = async () => {
    const parsed = Number(draft);
    if (draft.trim() === "" || !Number.isInteger(parsed) || Math.abs(parsed) > MAX_RELATION_LAG_DAYS) {
      setDraft(String(lag));
      setToast({
        type: "error",
        title: t("toast.error"),
        message: t("issue.relation.lag.invalid", { max: MAX_RELATION_LAG_DAYS }),
      });
      return;
    }
    if (parsed === lag) return;
    try {
      await updateRelationLag(workspaceSlug, projectId, issueId, relationKey, relatedIssueId, parsed);
    } catch (error) {
      setDraft(String(lag));
      setToast({
        type: "error",
        title: t("toast.error"),
        message: getIssueApiErrorMessage(error, t("issue.relation.lag.update_failed"), t),
      });
    }
  };

  return (
    <label className="flex items-center gap-1 text-11 text-tertiary" title={t("issue.relation.lag.hint")}>
      <span>{t("issue.relation.lag.label")}</span>
      <input
        type="number"
        inputMode="numeric"
        className="h-6 w-14 rounded-sm border border-subtle bg-surface-1 px-1 text-right text-11 text-primary disabled:bg-transparent"
        value={draft}
        min={-MAX_RELATION_LAG_DAYS}
        max={MAX_RELATION_LAG_DAYS}
        step={1}
        disabled={disabled}
        aria-label={t("issue.relation.lag.label")}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(event) => {
          // the row is a link: typing here must not reach it
          event.stopPropagation();
          if (event.key === "Enter") event.currentTarget.blur();
          if (event.key === "Escape") setDraft(String(lag));
        }}
      />
    </label>
  );
});

/** Days of lag of a timeline relation, shown and edited next to the related work item. */
export const RelationLag = observer(function RelationLag(props: Props) {
  const { issueId, relationKey, relatedIssueId, disabled, issueServiceType = EIssueServiceType.ISSUES } = props;
  const {
    relation: { getRelationLag },
  } = useIssueDetail(issueServiceType);
  const lag = getRelationLag(issueId, relationKey, relatedIssueId);

  if (disabled && lag === 0) return null;

  return <RelationLagInput key={lag} {...props} lag={lag} />;
});
