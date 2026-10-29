/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { KeyOutline } from "@makeplane/propel/icons";
import type { TOidcProviderOption } from "@plane/types";
// assets
import googleLogo from "@/app/assets/logos/google-logo.svg?url";
import microsoftLogo from "@/app/assets/logos/microsoft-logo.svg?url";

type Props = {
  icon: TOidcProviderOption["icon"];
  name: string;
  size: number;
};

export function OidcProviderIcon(props: Props) {
  const { icon, name, size } = props;
  if (icon === "microsoft") return <img src={microsoftLogo} height={size} width={size} alt={`${name} Logo`} />;
  if (icon === "google") return <img src={googleLogo} height={size} width={size} alt={`${name} Logo`} />;
  return <KeyOutline style={{ height: size, width: size }} className="p-0.5 text-tertiary" />;
}
