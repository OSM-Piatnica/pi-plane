/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from the timeline colours of inomotech-foss/paperplane (AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { DEFAULT_TIMELINE_COLOR_BY } from "@plane/constants";
import type { TTimelineColorBy } from "@plane/types";

const hashIdentifier = (identifier: string) => {
  let hash = 0;
  for (let index = 0; index < identifier.length; index++) hash = (hash * 31 + identifier.charCodeAt(index)) | 0;
  return Math.abs(hash);
};

/** Palette colour for a work item key, stepping by sequence id from a per-project offset. */
export const getWorkItemKeyColor = (
  projectIdentifier: string | undefined,
  sequenceId: number | undefined,
  palette: readonly string[]
): string | undefined => {
  if (sequenceId === undefined || palette.length === 0) return undefined;
  return palette[(hashIdentifier(projectIdentifier ?? "") + Math.abs(sequenceId)) % palette.length];
};

/**
 * Bar colour for a work item; key mode falls back to the state colour when there is no key yet, department mode
 * (RACI) takes the colour of the first responsible department and falls back to the state colour without one.
 */
export const getBarColor = (args: {
  colorBy: TTimelineColorBy | undefined;
  stateColor: string | undefined;
  projectIdentifier: string | undefined;
  sequenceId: number | undefined;
  palette: readonly string[];
  /** The colours of the responsible departments, in their order (department mode only). */
  departmentColors?: readonly string[];
}): string | undefined => {
  const { colorBy = DEFAULT_TIMELINE_COLOR_BY, stateColor, projectIdentifier, sequenceId, palette } = args;
  if (colorBy === "department") return args.departmentColors?.find((color) => !!color) ?? stateColor;
  if (colorBy !== "key") return stateColor;
  return getWorkItemKeyColor(projectIdentifier, sequenceId, palette) ?? stateColor;
};
