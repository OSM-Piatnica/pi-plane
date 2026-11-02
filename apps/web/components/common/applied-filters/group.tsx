/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { CloseOutline } from "@makeplane/propel/icons";
import { getGroupFilterValueLabel } from "@plane/utils";
// hooks
import { useFilterableUserGroups } from "@/hooks/use-filterable-user-groups";

type Props = {
  handleRemove: (val: string) => void;
  values: string[];
  editable: boolean | undefined;
};

/** The chips of the applied group filter of the module and cycle lists. */
export const AppliedGroupFilters = observer(function AppliedGroupFilters(props: Props) {
  const { handleRemove, values, editable } = props;
  const { t } = useTranslation();
  // router
  const { workspaceSlug } = useParams();
  // hooks
  const { groups } = useFilterableUserGroups(workspaceSlug?.toString());

  return (
    <>
      {values.map((value) => {
        // a group the person may not filter by (any more) stays removable under its id's place
        const label =
          getGroupFilterValueLabel(value, groups ?? [], t) ?? (groups ? t("group_filter.unknown_group") : "…");

        return (
          <div key={value} className="flex items-center gap-1 rounded-sm bg-layer-1 p-1 text-11">
            <span className="normal-case">{label}</span>
            {editable && (
              <button
                type="button"
                aria-label={t("remove")}
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
