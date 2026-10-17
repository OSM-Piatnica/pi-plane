/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";

import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Collapsible } from "@makeplane/propel/components/collapsible";

type Props = {
  openDeleteModal: () => void;
};

export function WebhookDeleteSection(props: Props) {
  const { openDeleteModal } = props;
  // translation
  const { t } = useTranslation();
  // states
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="w-full border-t border-subtle">
      <Collapsible
        open={isOpen}
        onOpenChange={setIsOpen}
        trigger={<span className="text-16 tracking-tight">{t("project_components.webhooks.danger_zone")}</span>}
      >
        <div className="flex flex-col gap-8">
          <span className="text-13 tracking-tight">{t("project_components.webhooks.danger_zone_description")}</span>
          <div>
            <Button
              variant="danger"
              size="md"
              stretch="auto"
              label={t("project_components.webhooks.delete_title")}
              onClick={openDeleteModal}
            />
          </div>
        </div>
      </Collapsible>
    </div>
  );
}
