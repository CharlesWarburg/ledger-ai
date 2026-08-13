import Link from "next/link";
import Image from "next/image";
import type { ReactNode } from "react";

import type { UserResponse } from "@/lib/api/types";
import { LogoutButton } from "@/components/auth/logout-button";

import { AppNav } from "./app-nav";
import { SettingsLink } from "./settings-link";

export function AppShell({ children, user }: { children: ReactNode; user: UserResponse }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link aria-label="Ledger home" className="product-brand" href="/dashboard">
          <Image alt="" className="product-logo" height={83} src="/ledger-mark.svg" width={64} />
        </Link>
        <AppNav />
        <div className="sidebar-foot">
          <SettingsLink />
          <div className="user-copy">
            <strong>{user.email}</strong>
            <span>{user.role} account</span>
          </div>
          <LogoutButton compact />
        </div>
      </aside>

      <div className="shell-content">
        <header className="mobile-header">
          <Link aria-label="Ledger home" className="product-brand" href="/dashboard">
            <Image alt="" className="product-logo" height={83} src="/ledger-mark.svg" width={64} />
          </Link>
          <SettingsLink />
        </header>
        <main className="page-content">{children}</main>
        <AppNav mobile />
      </div>
    </div>
  );
}
