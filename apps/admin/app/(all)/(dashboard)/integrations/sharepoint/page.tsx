/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { FolderSync } from "lucide-react";
// plane internal packages
import { Switch } from "@makeplane/propel/components/switch";
import { setPromiseToast } from "@plane/blocks/toast";
// components
import { AuthenticationMethodCard } from "@/components/authentication/authentication-method-card";
import { PageWrapper } from "@/components/common/page-wrapper";
import { Skeleton } from "@/components/common/skeleton";
// hooks
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceSharePointConfigForm } from "./form";

const InstanceSharePointPage = observer(function InstanceSharePointPage(_props: Route.ComponentProps) {
  // store
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();
  // state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const isEnabled = formattedConfig?.IS_SHAREPOINT_ENABLED === "1";
  const hasCredentials =
    Boolean(formattedConfig?.SHAREPOINT_TENANT_ID) &&
    Boolean(formattedConfig?.SHAREPOINT_CLIENT_ID) &&
    Boolean(formattedConfig?.SHAREPOINT_CLIENT_SECRET);
  // Turning it off always works; turning it on needs something to sign in with
  const canToggle = Boolean(formattedConfig) && !isSubmitting && (isEnabled || hasCredentials);

  const toggle = async () => {
    const value = isEnabled ? "0" : "1";
    setIsSubmitting(true);
    const updateConfigPromise = updateInstanceConfigurations({ IS_SHAREPOINT_ENABLED: value });

    setPromiseToast(updateConfigPromise, {
      loading: "Saving configuration",
      success: {
        title: "Configuration saved",
        message: () => `SharePoint is now ${value === "1" ? "enabled" : "disabled"}.`,
      },
      error: {
        title: "Error",
        message: () => "Failed to save configuration",
      },
    });

    try {
      await updateConfigPromise;
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper
      customHeader={
        <AuthenticationMethodCard
          name="SharePoint"
          description={
            hasCredentials || isEnabled
              ? "Keep documents of work items in SharePoint document libraries, through Microsoft Graph."
              : "Save the credentials of the app registration below, then switch SharePoint on."
          }
          icon={<FolderSync className="h-5 w-5 text-secondary" aria-hidden="true" />}
          config={
            <Switch
              aria-label="Enable SharePoint"
              checked={isEnabled}
              onCheckedChange={() => {
                void toggle();
              }}
              size="sm"
              disabled={!canToggle}
            />
          }
          disabled={!canToggle}
          withBorder={false}
        />
      }
    >
      {formattedConfig ? (
        <InstanceSharePointConfigForm config={formattedConfig} />
      ) : (
        <Skeleton className="space-y-8">
          <Skeleton.Item height="50px" width="25%" />
          <Skeleton.Item height="50px" />
          <Skeleton.Item height="50px" />
          <Skeleton.Item height="50px" />
          <Skeleton.Item height="50px" width="50%" />
        </Skeleton>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "SharePoint - God Mode" }];

export default InstanceSharePointPage;
