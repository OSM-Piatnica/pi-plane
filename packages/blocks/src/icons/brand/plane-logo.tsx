/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import * as React from "react";
import { PI_PLANE_MARK_DATA_URI, PI_PLANE_MARK_HEIGHT, PI_PLANE_MARK_WIDTH } from "./pi-plane-mark";

export type PlaneLogoProps = React.ComponentPropsWithoutRef<"svg">;

export function PlaneLogo({ width = "52", height = "52", className }: PlaneLogoProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 180 192"
      preserveAspectRatio="xMidYMid meet"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Pi-Plane"
    >
      <image href={PI_PLANE_MARK_DATA_URI} width={PI_PLANE_MARK_WIDTH} height={PI_PLANE_MARK_HEIGHT} />
    </svg>
  );
}
