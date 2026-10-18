/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CircleDashed } from "lucide-react";

interface IHeaderGroupByCard {
  groupID: string;
  icon?: React.ReactNode;
  title: string;
  count: number;
  toggleListGroup: (id: string) => void;
}

export const HeaderGroupByCard = observer(function HeaderGroupByCard(props: IHeaderGroupByCard) {
  const { groupID, icon, title, count, toggleListGroup } = props;

  return (
    <>
      <button
        type="button"
        className="group/list-header relative flex w-full shrink-0 items-center gap-2 px-2 py-1 py-1.5 text-left hover:bg-layer-transparent-hover"
        onClick={() => toggleListGroup(groupID)}
      >
        <div className="grid size-3.5 shrink-0 place-items-center overflow-hidden">
          {icon ?? <CircleDashed className="size-3.5" strokeWidth={2} />}
        </div>

        <div className="relative flex w-full cursor-pointer items-center gap-1 overflow-hidden">
          <div className="line-clamp-1 inline-block truncate font-medium text-primary">{title}</div>
          <div className="pl-2 text-13 font-medium text-tertiary">{count || 0}</div>
        </div>
      </button>
    </>
  );
});
