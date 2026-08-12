"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LogoutButton({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await fetch("/api/session", { method: "DELETE" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button aria-label="Sign out" className={compact ? "signout-button compact" : "signout-button"} disabled={pending} onClick={logout} type="button">
      {pending ? "…" : compact ? "↗" : "Sign out"}
    </button>
  );
}
