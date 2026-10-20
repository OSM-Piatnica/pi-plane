/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { splitTaggedText } from "../../helpers/tagged-text";

describe("splitTaggedText", () => {
  it("returns plain text unchanged", () => {
    expect(splitTaggedText("Your account is deactivated")).toEqual(["Your account is deactivated"]);
  });

  it("splits text around a tag", () => {
    expect(splitTaggedText("No account found. <link>Create one</link> to get started.")).toEqual([
      "No account found. ",
      { tag: "link", text: "Create one" },
      " to get started.",
    ]);
  });

  it("handles a tag at either end, which translations move around", () => {
    expect(splitTaggedText("<link>Zaloguj się</link> teraz.")).toEqual([
      { tag: "link", text: "Zaloguj się" },
      " teraz.",
    ]);
    expect(splitTaggedText('Search results: <query>"foo"</query>')).toEqual([
      "Search results: ",
      { tag: "query", text: '"foo"' },
    ]);
  });

  it("handles several different tags", () => {
    expect(splitTaggedText("<a>one</a> and <b>two</b>")).toEqual([
      { tag: "a", text: "one" },
      " and ",
      { tag: "b", text: "two" },
    ]);
  });

  it("treats a self-closing tag as a placeholder with no text", () => {
    expect(splitTaggedText("added this work item to the cycle <cycle/>.")).toEqual([
      "added this work item to the cycle ",
      { tag: "cycle", text: "" },
      ".",
    ]);
    expect(splitTaggedText("<user /> removed <issue/>")).toEqual([
      { tag: "user", text: "" },
      " removed ",
      { tag: "issue", text: "" },
    ]);
  });

  it("leaves a lone angle bracket alone", () => {
    expect(splitTaggedText("a < b")).toEqual(["a < b"]);
  });
});
