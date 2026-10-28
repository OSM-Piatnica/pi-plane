/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { GeneralConfigurationForm } from "./form";
import { UploadLimitSection } from "./upload-limit";
// types
import type { Route } from "./+types/page";

function GeneralPage() {
  const { instance, instanceAdmins } = useInstance();

  return (
    <PageWrapper
      header={{
        title: "General settings",
        description:
          "Change the name of your instance and instance admin e-mail addresses. Enable or disable telemetry in your instance. Set the largest file people can upload.",
      }}
    >
      {instance && instanceAdmins && <GeneralConfigurationForm instance={instance} instanceAdmins={instanceAdmins} />}
      <UploadLimitSection />
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [{ title: "General Settings - God Mode" }];

export default observer(GeneralPage);
