import Link from "next/link";
import type { ReactNode } from "react";

import type { UserResponse } from "@/lib/api/types";
import { LogoutButton } from "@/components/auth/logout-button";

import { AppNav } from "./app-nav";

export function AppShell({ children, user }: { children: ReactNode; user: UserResponse }) {
  const initial = user.email.charAt(0).toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="product-brand" href="/dashboard">
          <span className="product-mark">L</span>
          <span>Ledger</span>
        </Link>
        <AppNav />
        <div className="sidebar-foot">
          <div className="user-avatar">{initial}</div>
          <div className="user-copy">
            <strong>{user.email}</strong>
            <span>{user.role} account</span>
          </div>
          <LogoutButton compact />
        </div>
      </aside>

      <div className="shell-content">
        <header className="mobile-header">
          <Link className="product-brand" href="/dashboard">
            <span className="product-mark">L</span>
            <span>Ledger</span>
          </Link>
          <div className="user-avatar">{initial}</div>
        </header>
        <main className="page-content">{children}</main>
        <AppNav mobile />
      </div>
    </div>
  );
}
