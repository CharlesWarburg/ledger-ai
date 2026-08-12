"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LogoutButton() {
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
    <button className="ghost-button" disabled={pending} onClick={logout} type="button">
      {pending ? "Signing out…" : "Sign out"}
    </button>
  );
}
