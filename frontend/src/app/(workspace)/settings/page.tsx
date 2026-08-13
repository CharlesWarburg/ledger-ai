import { redirect } from "next/navigation";

import { SettingsView } from "@/components/settings/settings-view";
import { getCurrentUser } from "@/lib/auth/backend";
import { getSessionToken } from "@/lib/auth/session";

export default async function SettingsPage() {
  const token = await getSessionToken();
  if (!token) redirect("/login");
  const user = await getCurrentUser(token).catch(() => null);
  if (!user) redirect("/login");
  return <SettingsView user={user} />;
}
