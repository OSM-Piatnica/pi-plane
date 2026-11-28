/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CloseOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { PROJECT_NO_INITIATIVE } from "@plane/utils";
import { InitiativeIcon } from "@/components/initiatives/properties";
import { useInitiative } from "@/hooks/store/use-initiative";

type Props = {
  handleRemove: (val: string) => void;
  values: string[];
  editable: boolean | undefined;
};

/** The applied initiative filter: "No initiative", goals and initiatives by name */
export const AppliedInitiativeFilters = observer(function AppliedInitiativeFilters(props: Props) {
  const { handleRemove, values, editable } = props;
  const { t } = useTranslation();
  const { getInitiativeById } = useInitiative();

  return (
    <>
      {values.map((value) => {
        const initiative = value === PROJECT_NO_INITIATIVE ? undefined : getInitiativeById(value);
        const label =
          value === PROJECT_NO_INITIATIVE
            ? t("initiatives.project_list.no_initiative")
            : (initiative?.name ?? t("initiatives.kind.initiative"));
        return (
          <div key={value} className="flex items-center gap-1 rounded-sm bg-layer-1 px-1.5 py-1 text-11">
            {initiative && <InitiativeIcon kind={initiative.kind} status={initiative.status} className="size-3" />}
            <span className="max-w-40 truncate">{label}</span>
            {editable && (
              <button
                type="button"
                className="grid place-items-center text-tertiary hover:text-secondary"
                onClick={() => handleRemove(value)}
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
