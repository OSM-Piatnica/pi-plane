import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { mutate } from "swr";
import { PROJECT_IMPORT_SERVICES_LIST } from "@/constants/fetch-keys";
import { ImportForm } from "./import-form";
import { PrevImports } from "./prev-imports";

export const ImportGuide = observer(function ImportGuide() {
  const { workspaceSlug } = useParams();
  const per_page = 10;
  const [cursor, setCursor] = useState<string | undefined>(`10:0:0`);

  return (
    <div className="flex size-full flex-col gap-y-13">
      <ImportForm
        mutateServices={() => mutate(PROJECT_IMPORT_SERVICES_LIST(workspaceSlug as string, `${cursor}`, `${per_page}`))}
      />
      <PrevImports workspaceSlug={workspaceSlug as string} cursor={cursor} per_page={per_page} setCursor={setCursor} />
    </div>
  );
});
