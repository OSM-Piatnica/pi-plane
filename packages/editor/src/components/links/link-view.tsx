/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { Editor } from "@tiptap/react";
import type { CSSProperties } from "react";
import { useState } from "react";
// components
import { LinkEditView, LinkPreview } from "@/components/links";

export type LinkViews = "LinkPreview" | "LinkEditView";

export type LinkViewProps = {
  view?: LinkViews;
  editor: Editor;
  from: number;
  to: number;
  url: string;
  text?: string;
  closeLinkView: () => void;
};

export function LinkView(props: LinkViewProps & { style: CSSProperties }) {
  const [currentView, setCurrentView] = useState<LinkViews>(props.view ?? "LinkPreview");
  const [prevFrom, setPrevFrom] = useState(props.from);

  const switchView = (view: LinkViews) => {
    setCurrentView(view);
  };

  // reset to the preview whenever the link position changes (adjusting state during render)
  if (props.from !== prevFrom) {
    setPrevFrom(props.from);
    setCurrentView("LinkPreview");
  }

  return (
    <>
      {currentView === "LinkPreview" && <LinkPreview viewProps={props} switchView={switchView} />}
      {currentView === "LinkEditView" && <LinkEditView viewProps={props} switchView={switchView} />}
    </>
  );
}
