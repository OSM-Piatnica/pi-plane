/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React, { useState } from "react";
import { observer } from "mobx-react";
import { HelpOutline, MembersOutline, PagesOutline } from "@makeplane/propel/icons";
import { PI_PLANE_DOCS_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// ui
import { Icon } from "@makeplane/propel/components/icon";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@makeplane/propel/components/menu";
// components
import { ProductUpdatesModal } from "@/components/global";
import { ContactWorkspaceAdminsModal } from "@/components/workspace/contact-admins/contact-admins-modal";
import { useContactableAdmins } from "@/components/workspace/contact-admins/use-contactable-admins";
import { AppSidebarItem } from "@/components/sidebar/sidebar-item";
// hooks
import { usePowerK } from "@/hooks/store/use-power-k";
import { PlaneVersionNumber } from "@/components/global";

export const HelpMenuRoot = observer(function HelpMenuRoot() {
  // store hooks
  const { t } = useTranslation();
  const { toggleShortcutsListModal } = usePowerK();
  // somebody to write to: a workspace whose only admin is the person asking has nobody else to contact
  const { admins } = useContactableAdmins();
  // states
  const [isNeedHelpOpen, setIsNeedHelpOpen] = useState(false);
  const [isProductUpdatesModalOpen, setProductUpdatesModalOpen] = useState(false);
  const [isContactAdminsModalOpen, setContactAdminsModalOpen] = useState(false);

  return (
    <>
      <ProductUpdatesModal isOpen={isProductUpdatesModalOpen} handleClose={() => setProductUpdatesModalOpen(false)} />
      <ContactWorkspaceAdminsModal isOpen={isContactAdminsModalOpen} onClose={() => setContactAdminsModalOpen(false)} />

      <Menu onOpenChange={setIsNeedHelpOpen}>
        {/* propel: `AppSidebarItem` takes no arbitrary props, so it cannot be the Base UI trigger
            — the popup would have no element to anchor to. The trigger is a plain button wearing
            the same chrome, with the item's own icon part inside it. */}
        <MenuTrigger
          render={
            <button
              type="button"
              className="group flex flex-col items-center justify-center gap-0.5 text-tertiary"
              aria-label={t("power_k.group_titles.help")}
            >
              <AppSidebarItem.Icon icon={<HelpOutline className="size-5" />} highlight={isNeedHelpOpen} />
            </button>
          }
        />
        <MenuContent
          side="bottom"
          align="end"
          footer={
            <div className="text-11 text-secondary">
              <PlaneVersionNumber />
            </div>
          }
        >
          <MenuItem
            icon={<Icon icon={PagesOutline} tint="secondary" />}
            label={t("documentation")}
            onClick={() => window.open(PI_PLANE_DOCS_URL, "_blank", "noopener,noreferrer")}
          />
          {admins.length > 0 && (
            <MenuItem
              icon={<Icon icon={MembersOutline} tint="secondary" />}
              label={t("contact_workspace_admins.menu_label")}
              onClick={() => setContactAdminsModalOpen(true)}
            />
          )}
          <MenuSeparator />
          <MenuItem label={t("keyboard_shortcuts")} onClick={() => toggleShortcutsListModal(true)} />
          <MenuItem label={t("whats_new")} onClick={() => setProductUpdatesModalOpen(true)} />
        </MenuContent>
      </Menu>
    </>
  );
});
