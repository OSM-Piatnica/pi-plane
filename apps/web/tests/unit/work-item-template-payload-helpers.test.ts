/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  descriptionHtmlToPlain,
  plainTextToDescriptionHtml,
} from "../../app/(all)/[workspaceSlug]/(settings)/settings/(workspace)/work-item-templates/work-item-template-payload-helpers";

describe("descriptionHtmlToPlain", () => {
  it("turns paragraphs and line breaks into new lines", () => {
    expect(descriptionHtmlToPlain("<p>one<br/>two</p><p>three</p>")).toBe("one\ntwo\nthree");
  });

  it("decodes the three escaped characters once, in a single pass", () => {
    expect(descriptionHtmlToPlain("<p>a &amp; b &lt; c &gt; d</p>")).toBe("a & b < c > d");
    // an escaped entity stays an entity instead of being decoded twice
    expect(descriptionHtmlToPlain("<p>&amp;lt;</p>")).toBe("&lt;");
  });

  it("does not leave a tag behind when tags are nested inside each other", () => {
    expect(descriptionHtmlToPlain("<p><<b>script>alert(1)<</b>/script></p>")).not.toContain("<script");
  });

  it("round-trips text typed into the form", () => {
    const typed = "if a < b && b > c\nsecond line";
    expect(descriptionHtmlToPlain(plainTextToDescriptionHtml(typed))).toBe(typed);
  });

  it("handles empty input", () => {
    expect(descriptionHtmlToPlain(null)).toBe("");
    expect(descriptionHtmlToPlain("")).toBe("");
  });
});
