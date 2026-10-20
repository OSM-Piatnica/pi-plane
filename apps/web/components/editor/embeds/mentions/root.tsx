/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// local imports
import { EditorUserMention } from "./user";
import type { TCallbackMentionComponentProps } from "@plane/editor";

export function EditorMentionsRoot(props: TEditorMentionComponentProps) {
  const { entity_identifier, entity_name } = props;

  switch (entity_name) {
    case "user_mention":
      return <EditorUserMention id={entity_identifier} />;
    default:
      return <EditorAdditionalMentionsRoot {...props} />;
  }
}

// plane imports

export type TEditorMentionComponentProps = TCallbackMentionComponentProps;

export function EditorAdditionalMentionsRoot(_props: TEditorMentionComponentProps) {
  return null;
}
