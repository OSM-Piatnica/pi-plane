/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane types
import { StateGroupIcon } from "@plane/blocks/icons";
import { useTranslation } from "@plane/i18n";
import { getStateName } from "@/helpers/state-name";
import type { IState } from "@plane/types";
// components
import { PowerKModalCommandItem } from "@/components/power-k/ui/modal/command-item";

export type TPowerKProjectStatesMenuItemsProps = {
  handleSelect: (stateId: string) => void;
  projectId: string | undefined;
  selectedStateId: string | undefined;
  states: IState[];
  workspaceSlug: string;
};

export const PowerKProjectStatesMenuItems = observer(function PowerKProjectStatesMenuItems(
  props: TPowerKProjectStatesMenuItemsProps
) {
  const { handleSelect, selectedStateId, states } = props;
  // plane hooks
  const { t } = useTranslation();

  return (
    <>
      {states.map((state) => (
        <PowerKModalCommandItem
          key={state.id}
          iconNode={<StateGroupIcon stateGroup={state.group} color={state.color} className="size-3.5 shrink-0" />}
          label={getStateName(state.name, t)}
          isSelected={state.id === selectedStateId}
          onSelect={() => handleSelect(state.id)}
        />
      ))}
    </>
  );
});
