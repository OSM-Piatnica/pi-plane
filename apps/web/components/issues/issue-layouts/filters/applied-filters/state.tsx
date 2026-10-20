/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// icons
// plane imports
import { EIconSize } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { StateGroupIcon } from "@plane/blocks/icons";
import { CloseOutline } from "@makeplane/propel/icons";
import type { IState } from "@plane/types";
import { getStateName } from "@/helpers/state-name";

type Props = {
  handleRemove: (val: string) => void;
  states: IState[];
  values: string[];
  editable: boolean | undefined;
};

export const AppliedStateFilters = observer(function AppliedStateFilters(props: Props) {
  const { handleRemove, states, values, editable } = props;
  // plane hooks
  const { t } = useTranslation();

  return (
    <>
      {values.map((stateId) => {
        const stateDetails = states?.find((s) => s.id === stateId);

        if (!stateDetails) return null;

        return (
          <div key={stateId} className="flex items-center gap-1 rounded-sm bg-layer-1 p-1 text-11">
            <StateGroupIcon
              color={stateDetails.color}
              stateGroup={stateDetails.group}
              size={EIconSize.SM}
              percentage={stateDetails?.order}
            />
            {getStateName(stateDetails.name, t)}
            {editable && (
              <button
                type="button"
                className="grid place-items-center text-tertiary hover:text-secondary"
                onClick={() => handleRemove(stateId)}
              >
                <CloseOutline height={10} width={10} />
              </button>
            )}
          </div>
        );
      })}
    </>
  );
});
