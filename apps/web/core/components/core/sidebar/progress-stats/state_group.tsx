/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { StateGroupIcon } from "@plane/propel/icons";
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

export const StateGroupStatComponent = observer(function StateGroupStatComponent(props: TStateGroupStatComponent) {
  const { distribution, isEditable, totalIssuesCount, selectedStateGroups, handleStateGroupFiltersUpdate } = props;

  return (
    <div>
      {distribution.map((group, index) => (
        <SingleProgressStats
          // oxlint-disable-next-line react/no-array-index-key -- no stable unique key available
          key={index}
          title={
            <div className="flex items-center gap-2">
              <StateGroupIcon stateGroup={group.state as TStateGroups} />
              <span className="text-11 capitalize">{group.state}</span>
            </div>
          }
          completed={group.completed}
          total={totalIssuesCount}
          {...(isEditable && {
            onClick: () => group.state && handleStateGroupFiltersUpdate(group.state),
            selected: group.state ? selectedStateGroups.includes(group.state) : false,
          })}
        />
      ))}
    </div>
  );
});
