import { redirect } from "next/navigation";

import { getSessionToken } from "@/lib/auth/session";

export default async function HomePage() {
  redirect((await getSessionToken()) ? "/dashboard" : "/login");
}
