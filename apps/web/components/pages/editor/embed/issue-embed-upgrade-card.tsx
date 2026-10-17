/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { AnchorButton } from "@makeplane/propel/components/anchor-button";
import { cn } from "@plane/utils";
// components
import { ProIcon } from "@/components/common/pro-icon";

export function IssueEmbedUpgradeCard(props: any) {
  return (
    <div
      className={cn(
        "flex w-full items-center justify-between gap-5 rounded-md border-[0.5px] border-subtle bg-layer-1 px-5 py-2 shadow-raised-100 max-md:flex-wrap",
        {
          "border-2": props.selected,
        }
      )}
    >
      <div className="flex items-center gap-4">
        <ProIcon className="size-4 flex-shrink-0" />
        <p className="!text-14 text-secondary">
          Embed and access issues in pages seamlessly, upgrade to Plane Pro now.
        </p>
      </div>
      <AnchorButton
        href="https://plane.so/pro"
        target="_blank"
        rel="noopener noreferrer"
        variant="primary"
        size="md"
        label="Upgrade"
      />
    </div>
  );
}
