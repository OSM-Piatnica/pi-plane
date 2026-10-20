/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { Node } from "@tiptap/core";
import { mergeAttributes } from "@/helpers/merge-attributes";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";

type TableRowOptions = {
  HTMLAttributes: Record<string, unknown>;
};

export const TableRow = Node.create<TableRowOptions>({
  name: CORE_EXTENSIONS.TABLE_ROW,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      background: {
        default: null,
      },
      textColor: {
        default: null,
      },
    };
  },

  content: "(tableCell | tableHeader)*",

  tableRole: "row",

  parseHTML() {
    return [{ tag: "tr" }];
  },

  renderHTML({ HTMLAttributes }) {
    const style = HTMLAttributes.background
      ? `background-color: ${HTMLAttributes.background}; color: ${HTMLAttributes.textColor}`
      : "";

    const attributes = mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, { style });

    return ["tr", attributes, 0];
  },
});
