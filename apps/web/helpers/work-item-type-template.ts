/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isEmptyHtmlString, sanitizeHTML } from "@plane/utils";

/** The text of an HTML string without any white space, for telling whether a description was edited. */
const textOf = (html: string | null | undefined): string => sanitizeHTML(html ?? "").replace(/(\s|&nbsp;)+/g, "");

const EMPTY_DESCRIPTION = "<p></p>";

/**
 * What the description of a new work item becomes when its type is chosen, or `undefined` to leave it as it is.
 *
 * The type's template goes in only while the description is empty, or still holds the template the form put in for
 * the type chosen before (`lastApplied`) unchanged: what a person wrote is never replaced. Choosing a type without
 * a template takes such an untouched template away again.
 */
export const getDescriptionForTypeChange = (params: {
  currentHtml: string | null | undefined;
  template: string | null | undefined;
  lastApplied: string | null | undefined;
}): string | undefined => {
  const { currentHtml, template, lastApplied } = params;
  const isEmpty = isEmptyHtmlString(currentHtml ?? "");
  const holdsLastTemplate = !!lastApplied && textOf(currentHtml) === textOf(lastApplied);
  if (!isEmpty && !holdsLastTemplate) return undefined;
  const hasTemplate = !!template && textOf(template) !== "";
  if (hasTemplate) return template === currentHtml ? undefined : template;
  return holdsLastTemplate && !isEmpty ? EMPTY_DESCRIPTION : undefined;
};
