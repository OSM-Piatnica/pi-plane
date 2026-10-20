/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// assets
import emptyLabel from "@/app/assets/empty-state/empty_label.svg?url";
// components
import { SingleProgressStats } from "@/components/core/sidebar/single-progress-stats";

export type TLabelData = {
  id: string | undefined;
  title: string | undefined;
  color: string | undefined;
  completed: number;
  total: number;
}[];

type TLabelStatComponent = {
  selectedLabelIds: string[];
  handleLabelFiltersUpdate: (labelId: string | undefined) => void;
  distribution: TLabelData;
  isEditable?: boolean;
};

export const LabelStatComponent = observer(function LabelStatComponent(props: TLabelStatComponent) {
  const { distribution, isEditable, selectedLabelIds, handleLabelFiltersUpdate } = props;
  const { t } = useTranslation();
  const selectedLabelIdSet = new Set(selectedLabelIds);
  return (
    <div>
      {distribution && distribution.length > 0 ? (
        distribution.map((label, index) => {
          if (label.id) {
            return (
              <SingleProgressStats
                key={label.id}
                title={
                  <div className="flex items-center gap-2 truncate">
                    <span
                      className="block h-3 w-3 flex-shrink-0 rounded-full"
                      style={{
                        backgroundColor: label.color ?? "transparent",
                      }}
                    />
                    <span className="truncate text-11 text-ellipsis">{label.title ?? t("no_labels_yet")}</span>
                  </div>
                }
                completed={label.completed}
                total={label.total}
                {...(isEditable && {
                  onClick: () => handleLabelFiltersUpdate(label.id),
                  selected: label.id ? selectedLabelIdSet.has(label.id) : false,
                })}
              />
            );
          } else {
            return (
              <SingleProgressStats
                // react-doctor-disable-next-line no-array-index-as-key -- the no-label bucket has no id and the list is never reordered
                key={`no-label-${index}`} // oxlint-disable-line react/no-array-index-key
                title={
                  <div className="flex items-center gap-2">
                    <span
                      className="block h-3 w-3 rounded-full"
                      style={{
                        backgroundColor: label.color ?? "transparent",
                      }}
                    />
                    <span className="text-11">{label.title ?? t("no_labels_yet")}</span>
                  </div>
                }
                completed={label.completed}
                total={label.total}
              />
            );
          }
        })
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-layer-1">
            <img src={emptyLabel} className="h-12 w-12 object-contain" alt="empty label" />
          </div>
          <h6 className="text-14 text-tertiary">{t("no_labels_yet")}</h6>
        </div>
      )}
    </div>
  );
});
