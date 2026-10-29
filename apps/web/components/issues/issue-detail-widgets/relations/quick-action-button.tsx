/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";

import { useTranslation } from "@plane/i18n";
import { AddOutline } from "@makeplane/propel/icons";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
// plane imports
import type { TIssueServiceType, TIssueRelationTypes } from "@plane/types";
// hooks
import { filterEnabledRelationOptions } from "@/helpers/relation-type-toggles";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
// components
import { handleTriggerClick, handleTriggerKeyDown } from "@/components/common/trigger-guard";
import { useTimeLineRelationOptions } from "@/components/relations";

type Props = {
  issueId: string;
  /** Rendered as the trigger itself (not nested inside one); must forward ref and props to a `<button>`. */
  customButton?: React.ReactElement;
  disabled?: boolean;
  issueServiceType: TIssueServiceType;
};

export const RelationActionButton = observer(function RelationActionButton(props: Props) {
  const { customButton, issueId, disabled = false, issueServiceType } = props;
  const { t } = useTranslation();
  // store hooks
  const {
    toggleRelationModal,
    setRelationKey,
    issue: { getIssueById },
  } = useIssueDetail(issueServiceType);
  const { getProjectById } = useProject();

  const ISSUE_RELATION_OPTIONS = useTimeLineRelationOptions();
  const issueProject = getProjectById(getIssueById(issueId)?.project_id);

  // handlers
  const handleOnClick = (relationKey: TIssueRelationTypes) => {
    setRelationKey(relationKey);
    toggleRelationModal(issueId, relationKey);
  };

  return (
    <Menu>
      {customButton ? (
        <MenuTrigger
          disabled={disabled}
          render={customButton}
          onClick={handleTriggerClick}
          onKeyDown={handleTriggerKeyDown}
        />
      ) : (
        <MenuTrigger
          disabled={disabled}
          aria-label={t("issue.add.relation")}
          onClick={handleTriggerClick}
          onKeyDown={handleTriggerKeyDown}
        >
          <AddOutline className="h-4 w-4" />
        </MenuTrigger>
      )}
      <MenuContent side="bottom" align="start">
        {filterEnabledRelationOptions(Object.values(ISSUE_RELATION_OPTIONS), issueProject).map((item) => (
          <MenuItem
            key={item.key}
            icon={item.icon(12)}
            label={t(item.i18n_label)}
            onClick={(e) => {
              e.stopPropagation();
              handleOnClick(item.key);
            }}
          />
        ))}
      </MenuContent>
    </Menu>
  );
});
