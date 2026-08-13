import Link from "next/link";
import Image from "next/image";
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
          <Image alt="" className="auth-logo" height={83} src="/ledger-mark.svg" width={64} />
          <span>Ledger AI</span>
        </Link>
        <div className="auth-intro-copy">
          <p className="eyebrow">A clearer view of your finances</p>
          <h1>Financial clarity, without the busywork.</h1>
          <p>
            Keep customers, invoices, payments, documents, and financial insight in
            one focused workspace.
          </p>
        </div>
        <div className="auth-product-preview" aria-hidden="true">
          <div className="auth-preview-heading"><span>Financial control centre</span><i>Live</i></div>
          <div className="auth-preview-metrics"><span><small>Received</small><strong>£24.8k</strong></span><span><small>Outstanding</small><strong>£8.4k</strong></span><span><small>Overdue</small><strong>£1.2k</strong></span></div>
          <div className="auth-preview-chart">{[34,58,42,72,51,88,64,78].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div>
        </div>
        <p className="auth-footnote">Customers · Invoices · Payments · Intelligence</p>
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
