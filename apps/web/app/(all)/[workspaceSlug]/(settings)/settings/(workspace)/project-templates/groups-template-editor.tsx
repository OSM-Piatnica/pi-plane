/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import type { TUserGroup } from "@plane/types";
import {
  getAddableTemplateGroups,
  getGroupPaths,
  isTemplateGroupRole,
  TEMPLATE_GROUP_ROLES,
} from "@/helpers/project-template-groups";
import type { TProjectTemplateGroupField } from "./project-template-form.types";

type TProps = {
  value: TProjectTemplateGroupField[];
  onChange: (next: TProjectTemplateGroupField[]) => void;
  /** The workspace's groups; undefined while they load. */
  groups: TUserGroup[] | undefined;
};

const SELECT_CLASS = "h-8 rounded-md border border-subtle bg-surface-1 px-2 text-13 text-secondary";

function RoleSelect(props: { value: 15 | 5; onChange: (role: 15 | 5) => void }) {
  const { t } = useTranslation();
  return (
    <select
      aria-label={t("project_members.groups.role")}
      value={props.value}
      onChange={(event) => {
        const role = Number(event.target.value);
        if (isTemplateGroupRole(role)) props.onChange(role);
      }}
      className={SELECT_CLASS}
    >
      {TEMPLATE_GROUP_ROLES.map((role) => (
        <option key={role} value={role}>
          {role === 5 ? t("project_members.groups.role_guest") : t("project_members.groups.role_member")}
        </option>
      ))}
    </select>
  );
}

export const GroupsTemplateEditor = ({ value, onChange, groups }: TProps) => {
  const { t } = useTranslation();
  const [draftGroup, setDraftGroup] = useState("");
  const [draftRole, setDraftRole] = useState<15 | 5>(15);

  const paths = getGroupPaths(groups ?? []);
  const addable = getAddableTemplateGroups(groups ?? [], value);

  const onAdd = () => {
    if (!draftGroup) return;
    onChange([...value, { group: draftGroup, path: paths.get(draftGroup) ?? "", role: draftRole }]);
    setDraftGroup("");
  };

  return (
    <div className="rounded-md border border-subtle bg-surface-1">
      <div className="divide-y divide-subtle">
        {value.length === 0 ? (
          <p className="px-3 py-3 text-12 text-tertiary">
            {t("workspace_settings.settings.project_templates.form.groups_empty")}
          </p>
        ) : null}
        {value.map((row) => {
          // groups are loaded, and this one is not among them: it was deleted after the template was saved
          const missing = groups !== undefined && !paths.has(row.group);
          return (
            <div key={row.group} className="flex items-center gap-2 px-3 py-2">
              <div className="min-w-0 flex-1">
                <span className="truncate text-13 text-primary">{paths.get(row.group) ?? row.path}</span>
                {missing ? (
                  <span className="ml-2 text-12 text-danger-primary">
                    {t("workspace_settings.settings.project_templates.form.group_missing")}
                  </span>
                ) : null}
              </div>
              <RoleSelect
                value={row.role}
                onChange={(role) =>
                  onChange(value.map((item) => (item.group === row.group ? { ...item, role } : item)))
                }
              />
              <button
                type="button"
                className="rounded-md p-1 text-tertiary hover:bg-surface-2 hover:text-danger-primary"
                onClick={() => onChange(value.filter((item) => item.group !== row.group))}
                aria-label={t("remove")}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        })}
        <div className="flex flex-wrap items-center gap-2 px-3 py-2">
          <select
            aria-label={t("workspace_settings.settings.project_templates.form.select_group")}
            value={draftGroup}
            onChange={(event) => setDraftGroup(event.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">
              {addable.length === 0 && groups !== undefined
                ? t("workspace_settings.settings.project_templates.form.no_groups_available")
                : t("workspace_settings.settings.project_templates.form.select_group")}
            </option>
            {addable.map((group) => (
              <option key={group.id} value={group.id}>
                {group.path}
              </option>
            ))}
          </select>
          <RoleSelect value={draftRole} onChange={setDraftRole} />
          <Button
            stretch="auto"
            type="button"
            variant="secondary"
            size="sm"
            onClick={onAdd}
            disabled={!draftGroup}
            label={t("workspace_settings.settings.project_templates.form.add_group")}
          />
        </div>
      </div>
    </div>
  );
};
