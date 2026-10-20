/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { StateGroupIcon } from "@plane/blocks/icons";
import { STATE_GROUPS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TStateGroups } from "@plane/types";
// components
import { SingleProgressStats } from "@/components/core/sidebar/single-progress-stats";

export type TStateGroupData = {
  state: string | undefined;
  completed: number;
  total: number;
}[];

type TStateGroupStatComponent = {
  selectedStateGroups: string[];
  handleStateGroupFiltersUpdate: (stateGroup: string | undefined) => void;
  distribution: TStateGroupData;
  totalIssuesCount: number;
  isEditable?: boolean;
};

// the groups are fixed system categories with translation keys; an unknown value falls back to its raw text
const groupLabelKeys: Record<string, string> = Object.fromEntries(
  Object.values(STATE_GROUPS).map((group) => [group.key, group.i18n_label])
);

const getGroupLabel = (state: string | undefined, t: (key: string) => string) => {
  const key = state ? groupLabelKeys[state] : undefined;
  return key ? t(key) : state;
};

export const StateGroupStatComponent = observer(function StateGroupStatComponent(props: TStateGroupStatComponent) {
  const { distribution, isEditable, totalIssuesCount, selectedStateGroups, handleStateGroupFiltersUpdate } = props;
  // plane hooks
  const { t } = useTranslation();

  const selectedStateGroupSet = new Set(selectedStateGroups);

  return (
    <div>
      {distribution.map((group, index) => (
        <SingleProgressStats
          // react-doctor-disable-next-line no-array-index-as-key -- state-group rows have no id and the list is never reordered
          key={index} // oxlint-disable-line react/no-array-index-key
          title={
            <div className="flex items-center gap-2">
              <StateGroupIcon stateGroup={group.state as TStateGroups} />
              <span className="text-11 capitalize">{getGroupLabel(group.state, t)}</span>
            </div>
          }
          completed={group.completed}
          total={totalIssuesCount}
          {...(isEditable && {
            onClick: () => group.state && handleStateGroupFiltersUpdate(group.state),
            selected: group.state ? selectedStateGroupSet.has(group.state) : false,
          })}
        />
      ))}
    </div>
  );
});
