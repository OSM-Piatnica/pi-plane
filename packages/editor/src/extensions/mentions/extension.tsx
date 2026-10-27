/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { ReactNodeViewRenderer } from "@tiptap/react";
// types
import type { TMentionHandler } from "@/types";
// extension config
import { CustomMentionExtensionConfig } from "./extension-config";
import type { TMentionExtensionOptions } from "./extension-config";
// node view
import type { MentionNodeViewProps } from "./mention-node-view";
import { MentionNodeView } from "./mention-node-view";
// utils
import { renderMentionsDropdown } from "./utils";

export function CustomMentionExtension(props: TMentionHandler) {
  const { searchCallback, renderComponent, getMentionedEntityDetails } = props;
  return CustomMentionExtensionConfig.extend({
    addOptions(this) {
      return {
        ...this.parent!(),
        renderComponent,
        getMentionedEntityDetails,
      };
    },

    addNodeView() {
      return ReactNodeViewRenderer((nodeViewProps) => (
        <MentionNodeView {...nodeViewProps} node={nodeViewProps.node as MentionNodeViewProps["node"]} />
      ));
    },
  }).configure({
    suggestion: {
      render: renderMentionsDropdown({
        searchCallback,
      }),
      allowSpaces: true,
    },
  });
}
