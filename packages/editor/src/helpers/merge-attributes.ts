/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes as coreMergeAttributes } from "@tiptap/core";

// WORKAROUND for GHSA-cp6q-959q-f8rh (Dependabot alert #6): @tiptap/core's mergeAttributes() lets an own
// `__proto__` key (e.g. from JSON.parse) replace the prototype of the merged attributes, and ProseMirror then
// copies the inherited values (src, onerror, ...) onto the DOM element. The fix only ships in @tiptap/core
// >= 3.30.4, and there is no 2.x patch. Remove this wrapper and import mergeAttributes from "@tiptap/core"
// again once the editor is migrated to Tiptap v3.
const withoutProtoKey = (attributes: Record<string, unknown>): Record<string, unknown> =>
  Object.fromEntries(Object.entries(attributes).filter(([key]) => key !== "__proto__"));

type MergeAttributesInput = Record<string, unknown>;

export const mergeAttributes = (...items: MergeAttributesInput[]): Record<string, unknown> =>
  coreMergeAttributes(...items.map(withoutProtoKey));
