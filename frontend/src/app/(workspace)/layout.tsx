import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app/app-shell";
import { getCurrentUser } from "@/lib/auth/backend";
import { getSessionToken } from "@/lib/auth/session";

export default async function WorkspaceLayout({ children }: { children: ReactNode }) {
  const token = await getSessionToken();
  if (!token) redirect("/login");

  const user = await getCurrentUser(token).catch(() => null);
  if (!user) {
    redirect("/login");
  }

  return <AppShell user={user}>{children}</AppShell>;
}
