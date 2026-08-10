/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { RefObject } from "react";
import { observer } from "mobx-react";
import type { IGanttBlock } from "@plane/types";
import { DependencySideDraggable } from "./dependency-side-draggable";

type Props = {
  block: IGanttBlock;
  ganttContainerRef: RefObject<HTMLDivElement>;
};

export const RightDependencyDraggable = observer(function RightDependencyDraggable(props: Props) {
  return <DependencySideDraggable {...props} side="right" />;
});
