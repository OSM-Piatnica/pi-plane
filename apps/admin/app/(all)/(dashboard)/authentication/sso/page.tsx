/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import useSWR from "swr";
// plane internal packages
import { Switch } from "@makeplane/propel/components/switch";
import { setPromiseToast } from "@plane/blocks/toast";
import { OIDC_PROVIDER_DEFINITIONS } from "@plane/constants";
import type { TInstanceAuthenticationMethodKeys, TOidcProviderKey } from "@plane/types";
// components
import { AuthenticationMethodCard } from "@/components/authentication/authentication-method-card";
import { OidcProviderIcon } from "@/components/authentication/oidc-icon";
import { PageWrapper } from "@/components/common/page-wrapper";
import { Skeleton } from "@/components/common/skeleton";
import NotFound from "@/app/components/404";
// hooks
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceOidcConfigForm } from "./form";

const InstanceOidcAuthenticationPage = observer(function InstanceOidcAuthenticationPage() {
  const { provider: providerKey } = useParams();
  const provider = OIDC_PROVIDER_DEFINITIONS[providerKey as TOidcProviderKey];
  // store
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();
  // state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  if (!provider) return <NotFound />;

  const enabledKey = `IS_${provider.prefix}_ENABLED` as TInstanceAuthenticationMethodKeys;
  const isEnabled = (formattedConfig?.[enabledKey] ?? "") === "1";

  const updateConfig = async (key: TInstanceAuthenticationMethodKeys, value: string) => {
    setIsSubmitting(true);
    const updateConfigPromise = updateInstanceConfigurations({ [key]: value });
    setPromiseToast(updateConfigPromise, {
      loading: "Saving Configuration",
      success: {
        title: "Configuration saved",
        message: () => `${provider.name} authentication is now ${value === "1" ? "active" : "disabled"}.`,
      },
      error: {
        title: "Error",
        message: () => "Failed to save configuration",
      },
    });
    await updateConfigPromise
      .then(() => {
        setIsSubmitting(false);
        return;
      })
      .catch((err) => {
        console.error(err);
        setIsSubmitting(false);
      });
  };

  return (
    <PageWrapper
      customHeader={
        <AuthenticationMethodCard
          name={provider.name}
          description={provider.description}
          icon={<OidcProviderIcon icon={provider.icon} name={provider.name} size={24} />}
          config={
            <Switch
              aria-label={`Enable ${provider.name} authentication`}
              checked={isEnabled}
              onCheckedChange={() => void updateConfig(enabledKey, isEnabled ? "0" : "1")}
              size="sm"
              disabled={isSubmitting || !formattedConfig}
            />
          }
          disabled={isSubmitting || !formattedConfig}
          withBorder={false}
        />
      }
    >
      {formattedConfig ? (
        <InstanceOidcConfigForm key={provider.key} provider={provider} config={formattedConfig} />
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
export const meta: Route.MetaFunction = () => [{ title: "Single sign-on Authentication - God Mode" }];

export default InstanceOidcAuthenticationPage;
