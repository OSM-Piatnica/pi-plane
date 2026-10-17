/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import {
  Menu,
  MenuCheckboxItem,
  MenuContent,
  MenuGroup,
  MenuLabel,
  MenuTrigger,
} from "@makeplane/propel/components/menu";
import { ChevronDownOutline } from "@makeplane/propel/icons";
import { EUserProjectRoles, EUserWorkspaceRoles } from "@plane/types";

interface IRoleOption {
  value: string;
  label: string;
}

type Props = {
  appliedFilters: string[] | null;
  handleUpdate: (role: string) => void;
  memberType: "project" | "workspace";
};

const PROJECT_ROLE_OPTIONS: IRoleOption[] = [
  { value: String(EUserProjectRoles.ADMIN), label: "role_details.admin.title" },
  { value: String(EUserProjectRoles.MEMBER), label: "role_details.member.title" },
  { value: String(EUserProjectRoles.GUEST), label: "role_details.guest.title" },
];

const WORKSPACE_ROLE_OPTIONS: IRoleOption[] = [
  { value: String(EUserWorkspaceRoles.ADMIN), label: "role_details.admin.title" },
  { value: String(EUserWorkspaceRoles.MEMBER), label: "role_details.member.title" },
  { value: String(EUserWorkspaceRoles.GUEST), label: "role_details.guest.title" },
  { value: "suspended", label: "project_components.shared.suspended" },
];

// Dropdown component for member list filters
export const MemberListFiltersDropdown = observer(function MemberListFiltersDropdown(props: Props) {
  const { appliedFilters, handleUpdate, memberType } = props;
  // plane hooks
  const { t } = useTranslation();
  // derived values
  const roleOptions = memberType === "project" ? PROJECT_ROLE_OPTIONS : WORKSPACE_ROLE_OPTIONS;
  const appliedFiltersCount = appliedFilters?.length ?? 0;
  const appliedFilterSet = new Set(appliedFilters);

  return (
    <Menu>
      <div className="relative w-fit">
        <MenuTrigger
          render={
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              label={t("common.filters")}
              icon={<Icon icon={<ChevronDownOutline className="h-3 w-3" />} />}
              iconPosition="end"
            />
          }
        />
        {appliedFiltersCount > 0 && <div className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-accent-primary" />}
      </div>
      <MenuContent side="bottom" align="start">
        <MenuGroup>
          <MenuLabel meta={appliedFiltersCount > 0 ? String(appliedFiltersCount) : undefined}>
            {t("project_components.shared.roles")}
          </MenuLabel>
          {roleOptions.map((role) => (
            <MenuCheckboxItem
              key={`role-${role.value}`}
              label={t(role.label)}
              checked={appliedFilterSet.has(role.value)}
              onCheckedChange={() => handleUpdate(role.value)}
            />
          ))}
        </MenuGroup>
      </MenuContent>
    </Menu>
  );
});
