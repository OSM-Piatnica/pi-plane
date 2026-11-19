/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { FolderSync } from "lucide-react";
// plane internal packages
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { Button } from "@makeplane/propel/components/button";
import { SettingsOutline } from "@makeplane/propel/icons";
// components
import { AuthenticationMethodCard } from "@/components/authentication/authentication-method-card";
import { PageWrapper } from "@/components/common/page-wrapper";
import { Skeleton } from "@/components/common/skeleton";
// hooks
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";

const SHAREPOINT_HREF = "/integrations/sharepoint";

const InstanceIntegrationsPage = observer(function InstanceIntegrationsPage(_props: Route.ComponentProps) {
  // store hooks
  const { fetchInstanceConfigurations, formattedConfig } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const isSharePointConfigured =
    Boolean(formattedConfig?.SHAREPOINT_TENANT_ID) &&
    Boolean(formattedConfig?.SHAREPOINT_CLIENT_ID) &&
    Boolean(formattedConfig?.SHAREPOINT_CLIENT_SECRET);
  const isSharePointEnabled = formattedConfig?.IS_SHAREPOINT_ENABLED === "1";

  return (
    <PageWrapper
      header={{
        title: "Integrations",
        description: "Connect this instance to other systems your organisation uses.",
      }}
    >
      {formattedConfig ? (
        <div className="space-y-3">
          <AuthenticationMethodCard
            name="SharePoint"
            description="Keep documents of work items in SharePoint document libraries, through Microsoft Graph."
            icon={<FolderSync className="h-5 w-5 text-secondary" aria-hidden="true" />}
            config={
              isSharePointConfigured ? (
                <div className="flex items-center gap-4">
                  <span className="text-11 text-tertiary">{isSharePointEnabled ? "Enabled" : "Disabled"}</span>
                  <AnchorButton variant="primary" size="sm" render={<Link href={SHAREPOINT_HREF} />} label="Edit" />
                </div>
              ) : (
                <Button
                  variant="secondary"
                  size="sm"
                  stretch="auto"
                  nativeButton={false}
                  render={<Link href={SHAREPOINT_HREF} />}
                  icon={<SettingsOutline className="h-4 w-4 p-0.5 text-tertiary" />}
                  label="Configure"
                />
              )
            }
          />
        </div>
      ) : (
        <Skeleton className="space-y-10">
          <Skeleton.Item height="50px" width="75%" />
        </Skeleton>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Integrations - God Mode" }];

export default InstanceIntegrationsPage;
