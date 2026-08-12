import Link from "next/link";
import type { ReactNode } from "react";

export function ButtonLink({ children, href, secondary = false }: { children: ReactNode; href: string; secondary?: boolean }) {
  return <Link className={secondary ? "button secondary" : "button"} href={href}>{children}</Link>;
}
