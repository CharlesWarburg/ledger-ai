import { ButtonLink } from "@/components/ui/button-link";
import { PageHeading } from "@/components/ui/page-heading";

const summaryCards = [
  ["Total balance", "£0.00", "Across your Ledger workspace"],
  ["Outstanding", "£0.00", "No unpaid invoices yet"],
  ["Paid this month", "£0.00", "No payments recorded yet"],
];

const quickActions = [
  ["New customer", "/customers"],
  ["Create invoice", "/invoices"],
  ["Record payment", "/payments"],
  ["Upload document", "/documents"],
];

export default function DashboardPage() {
  return (
    <>
      <PageHeading actions={<ButtonLink href="/invoices">Create invoice</ButtonLink>} description="Here’s an overview of your business today." title="Good morning" />

      <section aria-label="Financial summary" className="summary-grid">
        {summaryCards.map(([label, value, detail], index) => (
          <article className={index === 0 ? "summary-card primary-summary" : "summary-card"} key={label}>
            <span>{label}</span><strong>{value}</strong><p>{detail}</p>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="panel activity-panel">
          <div className="panel-heading"><div><span className="kicker">Activity</span><h2>Recent transactions</h2></div><ButtonLink href="/payments" secondary>View all</ButtonLink></div>
          <div className="compact-empty"><div className="empty-orb">↗</div><h3>No activity yet</h3><p>Your invoices and payments will appear here.</p></div>
        </article>
        <aside className="panel quick-panel">
          <div className="panel-heading"><div><span className="kicker">Shortcuts</span><h2>Quick actions</h2></div></div>
          <div className="quick-list">{quickActions.map(([label, href]) => <ButtonLink href={href} key={label} secondary>{label}<span>→</span></ButtonLink>)}</div>
        </aside>
      </section>
    </>
  );
}
