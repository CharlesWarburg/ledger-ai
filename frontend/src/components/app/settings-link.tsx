"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AppIcon } from "./icons";

export function SettingsLink() {
  const active = usePathname().startsWith("/settings");
  return <Link aria-current={active ? "page" : undefined} aria-label="Settings" className={active ? "user-avatar settings-link active" : "user-avatar settings-link"} href="/settings"><AppIcon name="account" /></Link>;
}
