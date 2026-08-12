import Link from "next/link";
import type { ReactNode } from "react";

interface AuthLayoutProps {
  children: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
}

export function AuthLayout({ children, eyebrow, title, description }: AuthLayoutProps) {
  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Link className="brand" href="/">
          <span className="brand-mark">L</span>
          <span>Ledger AI</span>
        </Link>
        <div>
          <p className="eyebrow">A clearer view of your finances</p>
          <h1>Accounting work, without the busywork.</h1>
          <p>
            Keep customers, invoices, payments, documents, and financial insight in
            one focused workspace.
          </p>
        </div>
        <p className="auth-footnote">Built for small teams who want useful answers quickly.</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="muted-copy">{description}</p>
          {children}
        </div>
      </section>
    </main>
  );
}
