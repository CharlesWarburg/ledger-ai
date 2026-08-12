"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AppIcon, type IconName } from "./icons";

export const navigation: Array<{ href: string; icon: IconName; label: string }> = [
  { href: "/dashboard", icon: "dashboard", label: "Home" },
  { href: "/customers", icon: "customers", label: "Customers" },
  { href: "/invoices", icon: "invoices", label: "Invoices" },
  { href: "/payments", icon: "payments", label: "Payments" },
  { href: "/documents", icon: "documents", label: "Documents" },
  { href: "/insights", icon: "insights", label: "Insights" },
  { href: "/reports", icon: "reports", label: "Reports" },
];

export function AppNav({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  const items = mobile ? navigation.slice(0, 5) : navigation;

  return (
    <nav aria-label={mobile ? "Mobile navigation" : "Primary navigation"} className={mobile ? "mobile-nav" : "side-nav"}>
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link aria-current={active ? "page" : undefined} className={active ? "nav-link active" : "nav-link"} href={item.href} key={item.href}>
            <AppIcon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
