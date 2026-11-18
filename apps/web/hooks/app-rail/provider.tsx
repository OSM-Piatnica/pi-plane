/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useAppRailApps } from "@/components/app-rail/use-app-rail-apps";
import { AppRailVisibilityProvider as CoreProvider } from "@/lib/app-rail";

interface AppRailVisibilityProviderProps {
  children: React.ReactNode;
}

/**
 * AppRailVisibilityProvider
 * The rail is enabled only when the registry offers more than one app to switch between
 * (see docs/app-rail.md). With a single app it stays off, as before the registry.
 */
export const AppRailVisibilityProvider = observer(function AppRailVisibilityProvider({
  children,
}: AppRailVisibilityProviderProps) {
  const { hasMultipleApps } = useAppRailApps();

  return <CoreProvider isEnabled={hasMultipleApps}>{children}</CoreProvider>;
});
