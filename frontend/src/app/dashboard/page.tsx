import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/auth/logout-button";
import { getCurrentUser } from "@/lib/auth/backend";
import { getSessionToken } from "@/lib/auth/session";

const upcomingFeatures = [
  ["Customers", "Keep customer details and billing information together."],
  ["Invoices", "Create invoices, line items, and track every status."],
  ["Payments", "Record payments and see what is still outstanding."],
  ["Documents", "Upload files and review AI-extracted invoice data."],
];

export default async function DashboardPage() {
  const token = await getSessionToken();
  if (!token) {
    redirect("/login");
  }

  let user;
  try {
    user = await getCurrentUser(token);
  } catch {
    redirect("/login");
  }

  return (
    <div className="app-frame">
      <header className="app-header">
        <Link className="brand" href="/dashboard">
          <span className="brand-mark">L</span>
          <span>Ledger AI</span>
        </Link>
        <div className="header-account">
          <div>
            <strong>{user.email}</strong>
            <span>{user.role} account</span>
          </div>
          <LogoutButton />
        </div>
      </header>

      <main className="dashboard-main">
        <section className="welcome-card">
          <div>
            <p className="eyebrow">Your workspace</p>
            <h1>Welcome to Ledger AI.</h1>
            <p>
              Authentication is connected. This is the basic shell we will grow into
              your financial workspace.
            </p>
          </div>
          <div className="status-pill">
            <span />
            Backend connected
          </div>
        </section>

        <section aria-labelledby="next-up-title" className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Next up</p>
              <h2 id="next-up-title">The workspace taking shape</h2>
            </div>
            <span className="phase-label">Frontend phase 2</span>
          </div>
          <div className="feature-grid">
            {upcomingFeatures.map(([title, description], index) => (
              <article className="feature-card" key={title}>
                <span className="feature-number">0{index + 1}</span>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className="coming-soon">Coming soon</span>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
