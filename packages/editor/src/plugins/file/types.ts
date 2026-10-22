/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

/** The per-node-type file sets kept in the editor storage (`storage[nodeType][fileSetName]`). */
export type TFileStorage = Record<string, Record<string, Map<string, boolean> | undefined> | undefined>;

export type TFileNode = ProseMirrorNode & {
  attrs: {
    src: string;
    id: string;
  };
};
