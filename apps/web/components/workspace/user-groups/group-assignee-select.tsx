/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { CloseOutline } from "@makeplane/propel/icons";
// services
import { userGroupService } from "@/services/user-group.service";

type Props = {
  workspaceSlug: string;
  /** The groups the work item is assigned to. */
  value: string[];
  onChange: (groupIds: string[]) => void;
  disabled?: boolean;
};

/** Chips of the groups a work item is assigned to, and a list to add another one. */
export const GroupAssigneeSelect = observer(function GroupAssigneeSelect(props: Props) {
  const { workspaceSlug, value, onChange, disabled } = props;
  // translation
  const { t } = useTranslation();

  const { data: groups } = useSWR(`USER_GROUPS_${workspaceSlug}`, () => userGroupService.list(workspaceSlug));

  // derived values
  const groupNames = new Map((groups ?? []).map((group) => [group.id, group.name]));
  const selectable = (groups ?? []).filter((group) => !value.includes(group.id));

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {value.length === 0 && (
        <span className="text-13 text-tertiary">{t("workspace_settings.settings.groups.no_group_assignees")}</span>
      )}
      {value.map((groupId) => (
        <span
          key={groupId}
          className="flex items-center gap-1 rounded-full bg-layer-1 px-2 py-0.5 text-12 text-primary"
        >
          {groupNames.get(groupId) ?? groupId}
          {!disabled && (
            <button
              type="button"
              aria-label={t("remove")}
              className="text-secondary hover:text-primary"
              onClick={() => onChange(value.filter((id) => id !== groupId))}
            >
              <CloseOutline className="size-3" aria-hidden="true" />
            </button>
          )}
        </span>
      ))}
      {!disabled && selectable.length > 0 && (
        <select
          aria-label={t("workspace_settings.settings.groups.add_group_assignee")}
          value=""
          onChange={(event) => {
            if (event.target.value) onChange([...value, event.target.value]);
          }}
          className="h-6 rounded-md border border-subtle bg-surface-1 px-1.5 text-12 text-secondary"
        >
          <option value="">{t("workspace_settings.settings.groups.add_group_assignee")}</option>
          {selectable.map((group) => (
            <option key={group.id} value={group.id}>
              {group.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
});
