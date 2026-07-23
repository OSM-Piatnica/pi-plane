/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { mutate } from "swr";
// constants
import { PROJECT_IMPORT_SERVICES_LIST } from "@/constants/fetch-keys";
import { ImportForm } from "@/components/importer/import-form";
import { PrevImports } from "@/components/importer/prev-imports";
import { ProjectExportForm } from "./project-export-form";

export const ExportGuide = observer(function ExportGuide() {
  const { workspaceSlug } = useParams();
  const per_page = 10;
  const [importCursor, setImportCursor] = useState<string | undefined>(`10:0:0`);

  return (
    <div className="flex size-full flex-col gap-y-13">
      <div id="import">
        <ImportForm
          mutateServices={() =>
            mutate(PROJECT_IMPORT_SERVICES_LIST(workspaceSlug as string, `${importCursor}`, `${per_page}`))
          }
        />
      </div>
      <PrevImports
        workspaceSlug={workspaceSlug as string}
        cursor={importCursor}
        per_page={per_page}
        setCursor={setImportCursor}
      />
      <ProjectExportForm workspaceSlug={workspaceSlug as string} />
    </div>
  );
});
