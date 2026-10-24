/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
// icons
import { SettingsOutline } from "@makeplane/propel/icons";
// plane internal packages
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { Button } from "@makeplane/propel/components/button";
import { Switch } from "@makeplane/propel/components/switch";
import type { TOidcProviderDefinition } from "@plane/constants";
import type { TInstanceAuthenticationMethodKeys } from "@plane/types";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  provider: TOidcProviderDefinition;
  disabled: boolean;
  updateConfig: (key: TInstanceAuthenticationMethodKeys, value: string) => void;
};

/** Edit / enable switch of a single sign-on provider on the authentication page. */
export const OidcConfiguration = observer(function OidcConfiguration(props: Props) {
  const { provider, disabled, updateConfig } = props;
  // store
  const { formattedConfig } = useInstance();
  // derived values
  const enabledKey = `IS_${provider.prefix}_ENABLED` as TInstanceAuthenticationMethodKeys;
  const isEnabled = Boolean(parseInt(formattedConfig?.[enabledKey] ?? "0"));
  const isConfigured =
    !!formattedConfig?.[`${provider.prefix}_CLIENT_ID` as keyof typeof formattedConfig] &&
    !!formattedConfig?.[`${provider.prefix}_CLIENT_SECRET` as keyof typeof formattedConfig] &&
    provider.fields.every(
      (field) =>
        !field.required || !!formattedConfig?.[`${provider.prefix}_${field.name}` as keyof typeof formattedConfig]
    );
  const href = `/authentication/sso/${provider.key}`;

  return isConfigured ? (
    <div className="flex items-center gap-4">
      <AnchorButton variant="primary" size="sm" render={<Link href={href} />} label="Edit" />
      <Switch
        checked={isEnabled}
        onCheckedChange={() => updateConfig(enabledKey, isEnabled ? "0" : "1")}
        size="sm"
        aria-label={`Enable ${provider.name}`}
        disabled={disabled}
      />
    </div>
  ) : (
    <Button
      variant="secondary"
      size="sm"
      stretch="auto"
      nativeButton={false}
      render={<Link href={href} />}
      icon={<SettingsOutline className="h-4 w-4 p-0.5 text-tertiary" />}
      label="Configure"
    />
  );
});
