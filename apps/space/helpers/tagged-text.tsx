/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment } from "react";
import type { ReactNode } from "react";

export type TTaggedTextPart = string | { tag: string; text: string };

// `<tag>text</tag>` or a self-closing `<tag/>` placeholder
const TAG_PATTERN = /<(\w+)>(.*?)<\/\1>|<(\w+)\s*\/>/gs;

/**
 * Splits a translated string into plain text and `<tag>…</tag>` parts, so a translation can put
 * markup (a link, a highlighted word) wherever the language's word order needs it:
 * `"No account found. <link>Create one</link> to get started."`. A self-closing `<tag/>` marks where
 * a value that must not be spliced into the string (a user-supplied name) is rendered. Tags do not nest.
 */
export const splitTaggedText = (text: string): TTaggedTextPart[] => {
  const parts: TTaggedTextPart[] = [];
  let cursor = 0;
  for (const match of text.matchAll(TAG_PATTERN)) {
    const start = match.index ?? 0;
    if (start > cursor) parts.push(text.slice(cursor, start));
    parts.push({ tag: match[1] ?? match[3] ?? "", text: match[2] ?? "" });
    cursor = start + match[0].length;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return parts;
};

/** Renders {@link splitTaggedText} parts; a tag without a renderer keeps its text, unwrapped. */
export const renderTaggedText = (text: string, renderers: Record<string, (children: string) => ReactNode>): ReactNode =>
  splitTaggedText(text).map((part, index) => (
    // oxlint-disable-next-line react/no-array-index-key -- parts are positional and never reorder
    <Fragment key={index}>{typeof part === "string" ? part : (renderers[part.tag]?.(part.text) ?? part.text)}</Fragment>
  ));
