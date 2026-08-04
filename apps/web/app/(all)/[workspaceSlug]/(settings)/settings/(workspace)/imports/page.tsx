import { redirect } from "react-router";
import type { Route } from "./+types/page";

export const clientLoader = ({ params }: Route.ClientLoaderArgs) => {
  const { workspaceSlug } = params;
  throw redirect(`/${workspaceSlug}/settings/exports#import`);
};

export default function ImportsRedirectPage() {
  return null;
}
