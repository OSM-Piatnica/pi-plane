/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// layouts
import { DevErrorComponent } from "./dev";
import { ProdErrorComponent } from "./prod";

const handleReload = () => window.location.reload();
// A full navigation, not a router push: when the error comes from the router or a layout, a client-side
// navigation can land straight back in the same broken state.
const handleGoHome = () => window.location.assign("/");

export function CustomErrorComponent({ error }: { error: unknown }) {
  if (import.meta.env.DEV) {
    return <DevErrorComponent error={error} onGoHome={handleGoHome} onReload={handleReload} />;
  }

  return <ProdErrorComponent error={error} onGoHome={handleGoHome} onReload={handleReload} />;
}
