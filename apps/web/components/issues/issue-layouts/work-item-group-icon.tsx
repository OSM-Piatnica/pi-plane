/**
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from Hangar (szymczag/hangar, AGPL-3.0-only).
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { ParentOutline } from "@makeplane/propel/icons";
// hooks
import { useWorkItemReference } from "@/hooks/use-work-item-reference";

type Props = {
  workItemId: string;
};

/** Icon of a parent group. Resolving it also loads the group's work item for the group title. */
export const WorkItemGroupIcon = observer(function WorkItemGroupIcon(props: Props) {
  const { workItemId } = props;
  const { workspaceSlug, projectId } = useParams();
  useWorkItemReference(workspaceSlug?.toString(), projectId?.toString(), workItemId);

  return <ParentOutline className="h-3.5 w-3.5" />;
});
