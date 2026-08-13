"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiRequest, ApiError } from "@/lib/api";
import type { CustomerResponse, DashboardResponse, DocumentResponse, DocumentType, InvoiceCreate, InvoiceLineItemCreate, InvoiceResponse, InvoiceStatus, PaymentResponse } from "@/lib/api";
import { PageHeading } from "@/components/ui/page-heading";
import styles from "./receivables-board.module.css";

function cash(value: string | number, currency: string) { return new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value)); }
function msg(error: unknown) { return error instanceof ApiError ? error.message : "Dashboard could not load."; }
const dueWindows = [{ key: "overdue", label: "Overdue" }, { key: "week", label: "This week" }, { key: "month", label: "Next 30 days" }, { key: "later", label: "Later" }] as const;
const valueBands = [{ key: "high", label: "£5k+" }, { key: "medium", label: "£1k–£5k" }, { key: "low", label: "£500–£1k" }, { key: "small", label: "Under £500" }] as const;
type QuickAction = "upload" | "invoice";
type QuickLine = InvoiceLineItemCreate & { key: number };
const blankQuickLine = (key: number): QuickLine => ({ key, description: "", quantity: "1", unit_price: "0", vat_rate: "20" });

export function DashboardView() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [payments, setPayments] = useState<PaymentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currency, setCurrency] = useState("GBP");
  const [months, setMonths] = useState(12);
  const [status, setStatus] = useState<InvoiceStatus | "">("");
  const [customer, setCustomer] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [quickAction, setQuickAction] = useState<QuickAction | null>(null);
  const [quickBusy, setQuickBusy] = useState(false);
  const [quickError, setQuickError] = useState<string | null>(null);
  const [quickLines, setQuickLines] = useState<QuickLine[]>([blankQuickLine(1)]);
  const [nextQuickLine, setNextQuickLine] = useState(2);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiRequest<DashboardResponse>("/dashboard", { query: { currency, months, invoice_status: status || undefined, customer_id: customer || undefined, date_from: from || undefined, date_to: to || undefined } }),
      apiRequest<CustomerResponse[]>("/customers", { query: { limit: 100 } }),
      apiRequest<InvoiceResponse[]>("/invoices", { query: { limit: 100, currency, has_balance: true } }),
      apiRequest<PaymentResponse[]>("/payments", { query: { limit: 100, currency } }),
    ]).then(([dashboard, customerData, invoiceData, paymentData]) => {
      if (!cancelled) { setData(dashboard); setCustomers(customerData); setInvoices(invoiceData); setPayments(paymentData); setError(null); }
    }).catch((reason) => { if (!cancelled) setError(msg(reason)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [currency, months, status, customer, from, to]);

  const maxCash = Math.max(1, ...(data?.monthly_cash_flow.map((point) => Number(point.amount)) ?? []));
  const active = useMemo(() => [status, customer, from, to].filter(Boolean).length, [status, customer, from, to]);
  const customerNames = useMemo(() => new Map(customers.map((item) => [item.id, item.name])), [customers]);
  const paidByInvoice = useMemo(() => {
    const values = new Map<string, number>();
    payments.forEach((payment) => values.set(payment.invoice_id, (values.get(payment.invoice_id) ?? 0) + Number(payment.amount)));
    return values;
  }, [payments]);
  const receivables = useMemo(() => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    return invoices.filter((invoice) => (invoice.status === "sent" || invoice.status === "overdue") && (!status || invoice.status === status) && (!customer || invoice.customer_id === customer) && (!from || invoice.issue_date >= from) && (!to || invoice.issue_date <= to)).map((invoice) => {
      const balance = Math.max(0, Number(invoice.total) - (paidByInvoice.get(invoice.id) ?? 0));
      const days = Math.round((new Date(`${invoice.due_date}T00:00:00`).getTime() - today.getTime()) / 86_400_000);
      const window = days < 0 ? "overdue" : days <= 7 ? "week" : days <= 30 ? "month" : "later";
      return { ...invoice, balance, days, window };
    }).filter((invoice) => invoice.balance > 0).sort((a, b) => a.days - b.days);
  }, [invoices, paidByInvoice, status, customer, from, to]);

  const resetFilters = () => { setStatus(""); setCustomer(""); setFrom(""); setTo(""); };
  const openQuickAction = (action: QuickAction) => { setQuickAction(action); setQuickError(null); if (action === "invoice") { setQuickLines([blankQuickLine(1)]); setNextQuickLine(2); } };
  const closeQuickAction = () => { if (!quickBusy) setQuickAction(null); };
  const updateQuickLine = (key: number, field: keyof InvoiceLineItemCreate, value: string) => setQuickLines((lines) => lines.map((line) => line.key === key ? { ...line, [field]: value } : line));
  const addQuickLine = () => { setQuickLines((lines) => [...lines, blankQuickLine(nextQuickLine)]); setNextQuickLine((value) => value + 1); };
  async function submitQuickUpload(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setQuickBusy(true); setQuickError(null); try { await apiRequest<DocumentResponse>("/documents", { method: "POST", body: new FormData(event.currentTarget) }); setQuickAction(null); } catch (reason) { setQuickError(msg(reason)); } finally { setQuickBusy(false); } }
  async function submitQuickInvoice(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setQuickBusy(true); setQuickError(null); const form = new FormData(event.currentTarget); const payload: InvoiceCreate = { customer_id: String(form.get("customer_id")), invoice_number: String(form.get("invoice_number")).trim(), issue_date: String(form.get("issue_date")), due_date: String(form.get("due_date")), currency: String(form.get("currency")).trim().toUpperCase(), notes: String(form.get("notes") ?? "").trim() || null, line_items: quickLines.map(({ description, quantity, unit_price, vat_rate }) => ({ description: description.trim(), quantity, unit_price, vat_rate })) }; try { await apiRequest<InvoiceResponse>("/invoices", { method: "POST", body: payload }); setQuickAction(null); } catch (reason) { setQuickError(msg(reason)); } finally { setQuickBusy(false); } }

  return <div className="dashboard-stage">
    <PageHeading actions={<div className="dashboard-heading-actions"><button onClick={() => openQuickAction("upload")} type="button">Upload document</button><button className="dashboard-primary-action" onClick={() => openQuickAction("invoice")} type="button">New invoice <b>+</b></button></div>} description="A live view of money moving through your business." title="Financial control centre" />
    <div className="dashboard-filters">
      <label className="dashboard-filter-pill"><span>Currency</span><select aria-label="Currency" value={currency} onChange={(event) => setCurrency(event.target.value)}><option>GBP</option><option>USD</option><option>EUR</option></select></label>
      <label className="dashboard-filter-pill"><span>Period</span><select aria-label="Reporting period" value={months} onChange={(event) => setMonths(Number(event.target.value))}><option value={6}>Last 6 months</option><option value={12}>Last 12 months</option><option value={24}>Last 24 months</option></select></label>
      <label className="dashboard-filter-pill"><span>Status</span><select aria-label="Invoice status" value={status} onChange={(event) => setStatus(event.target.value as InvoiceStatus | "")}><option value="">All statuses</option>{["draft", "sent", "paid", "overdue", "cancelled"].map((item) => <option key={item}>{item}</option>)}</select></label>
      <label className="dashboard-filter-pill"><span>Customer</span><select aria-label="Customer" value={customer} onChange={(event) => setCustomer(event.target.value)}><option value="">All customers</option>{customers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <label className="dashboard-filter-pill"><span>From</span><input aria-label="From date" type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
      <label className="dashboard-filter-pill"><span>To</span><input aria-label="To date" type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
      {active ? <button onClick={resetFilters}>Clear {active}</button> : null}
    </div>
    {loading ? <div className="loading-grid">{[1, 2, 3, 4].map((item) => <div className="skeleton-card" key={item}><span /><span /><span /></div>)}</div> : error ? <div className="state-card error-state"><div className="state-icon">!</div><h2>Dashboard couldn’t load</h2><p>{error}</p></div> : data ? <>
      <section className="live-kpis">
        <Link className="kpi-revenue" href="/payments"><span><i />Revenue received</span><strong>{cash(data.kpis.total_revenue, data.currency)}</strong><small>For selected period <b>↗</b></small></Link>
        <Link className="kpi-outstanding" href="/invoices"><span><i />Outstanding</span><strong>{cash(data.kpis.outstanding_amount, data.currency)}</strong><small>Open invoice balances <b>↗</b></small></Link>
        <Link className="kpi-overdue" href="/invoices"><span><i />Overdue</span><strong>{cash(data.kpis.overdue_amount, data.currency)}</strong><small>Past their due date <b>↗</b></small></Link>
        <Link className="kpi-paid" href="/invoices"><span><i />Paid invoices</span><strong>{data.kpis.paid_invoice_count}</strong><small>Completed invoices <b>↗</b></small></Link>
      </section>
      <section className="dashboard-panels">
        <article className="panel cash-panel">
          <div className="panel-heading receipt-heading"><div><span className="kicker"><i />Cash flow</span><h2>Monthly receipts</h2></div><span className="receipt-summary">{cash(data.monthly_cash_flow.reduce((sum, point) => sum + Number(point.amount), 0) / Math.max(data.monthly_cash_flow.length, 1), data.currency)} avg</span></div>
          <div className="receipt-legend" aria-label="Receipt intensity"><span><i className="receipt-level receipt-level-empty" />No receipts</span><span><i className="receipt-level receipt-level-low" />Lower</span><span><i className="receipt-level receipt-level-high" />Higher</span></div>
          <div className="receipt-heatmap">{data.monthly_cash_flow.map((point) => { const amount = Number(point.amount); return <div className={`receipt-month${amount === 0 ? " is-empty" : ""}`} key={point.month} title={`${point.month}: ${cash(point.amount, data.currency)}`}><span className="receipt-cell" style={{ opacity: amount === 0 ? 1 : .28 + (amount / maxCash) * .72 }}><b>{amount ? cash(point.amount, data.currency) : "—"}</b></span><small>{new Date(point.month).toLocaleDateString("en-GB", { month: "short" })}</small></div>; })}</div>
        </article>
        <article className="panel recent-panel"><div className="panel-heading"><div><span className="kicker"><i />Latest</span><h2>Recent activity</h2></div><Link href="/invoices">View all ↗</Link></div>{data.recent_activity.length ? <div className="activity-list">{data.recent_activity.slice(0, 10).map((activity) => <Link href={activity.activity_type === "payment_received" ? "/payments" : "/invoices"} key={`${activity.activity_type}-${activity.entity_id}`}><span className="activity-dot">{activity.activity_type === "payment_received" ? "↓" : "↑"}</span><span><strong>{activity.description}</strong><small>{new Date(activity.occurred_at).toLocaleString("en-GB")}</small></span><strong>{activity.amount ? cash(activity.amount, data.currency) : ""}</strong></Link>)}</div> : <div className="compact-empty"><h3>No recent activity</h3><p>Invoices and payments will appear here.</p></div>}</article>
        <article className="panel status-panel receivables-panel">
          <div className="panel-heading"><div><span className="kicker"><i />Receivables</span><h2>Who owes what</h2></div><Link href="/invoices">View all ↗</Link></div>
          <div className={`${styles.board} receivables-board`}>
            <div className="receivables-corner"><span>Balance</span><small>Due window →</small></div>
            {dueWindows.map((window, index) => <div className={`receivable-column-heading ${window.key}`} style={{ gridColumn: index + 2 }} key={window.key}><span>{window.label}</span><small>{receivables.filter((item) => item.window === window.key).length}</small></div>)}
            {valueBands.map((band, index) => <div className="receivable-row-heading" style={{ gridRow: index + 2 }} key={band.key}>{band.label}</div>)}
            <div className="receivables-grid" aria-label="Outstanding invoices by balance and due date">
              {receivables.slice(0, 12).map((item, index) => {
                const column = dueWindows.findIndex((window) => window.key === item.window) + 1;
                const row = item.balance >= 5000 ? 1 : item.balance >= 1000 ? 2 : item.balance >= 500 ? 3 : 4;
                return <Link href="/invoices" className={`receivable-card${item.window === "overdue" ? " overdue" : ""}`} style={{ gridColumn: column, gridRow: row, transform: `translate(${index % 2 ? 5 : -3}px, ${index % 3 ? 4 : -3}px)` }} key={item.id}><span><strong>{customerNames.get(item.customer_id) ?? "Unknown customer"}</strong><small>{item.invoice_number} · Due {new Date(`${item.due_date}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</small></span><b>{cash(item.balance, item.currency)}</b></Link>;
              })}
              {!receivables.length ? <div className="receivables-board-empty">No outstanding invoices for these filters.</div> : null}
            </div>
          </div>
        </article>
      </section>
    </> : null}
    {quickAction ? <div className="quick-action-layer">
      <button aria-label="Close quick action" className="quick-action-backdrop" disabled={quickBusy} onClick={closeQuickAction} type="button" />
      <aside aria-modal="true" className="quick-action-drawer" role="dialog">
        <div className="quick-action-heading"><div><span>Quick action</span><h2>{quickAction === "upload" ? "Upload document" : "New invoice"}</h2></div><button aria-label="Close" disabled={quickBusy} onClick={closeQuickAction} type="button">×</button></div>
        {quickAction === "upload" ? <form className="quick-action-form" onSubmit={submitQuickUpload}>
          <div className="quick-action-scroll">
            <details className="quick-section" open><summary><span><i>01</i><strong>Choose document</strong><small>PDF, JPEG or PNG up to 10 MB</small></span><b>⌄</b></summary><label className="quick-dropzone"><input accept="application/pdf,image/jpeg,image/png" name="file" required type="file" /><span>↑</span><strong>Drop a file here</strong><small>or click to browse your computer</small></label></details>
            <details className="quick-section" open><summary><span><i>02</i><strong>Document type</strong><small>How Ledger AI should categorise it</small></span><b>⌄</b></summary><div className="quick-choice-grid">{([ ["other","General"],["receipt","Receipt"],["invoice_attachment","Invoice"] ] as [DocumentType,string][]).map(([value,label], index) => <label key={value}><input defaultChecked={index === 0} name="document_type" type="radio" value={value} /><span><i>{index === 0 ? "◇" : index === 1 ? "▣" : "□"}</i><strong>{label}</strong><small>{value === "other" ? "Other paperwork" : value === "receipt" ? "Proof of purchase" : "Invoice attachment"}</small></span></label>)}</div></details>
            {quickError ? <p className="form-error">{quickError}</p> : null}
          </div>
          <div className="quick-action-footer"><button className="quick-cancel" onClick={closeQuickAction} type="button">Cancel</button><button className="quick-submit" disabled={quickBusy}>{quickBusy ? "Uploading…" : "Upload document"}</button></div>
        </form> : <form className="quick-action-form" onSubmit={submitQuickInvoice}>
          <div className="quick-action-scroll">
            <details className="quick-section" open><summary><span><i>01</i><strong>Invoice details</strong><small>Customer, reference and payment dates</small></span><b>⌄</b></summary><div className="quick-fields"><label><span>Customer</span><select name="customer_id" required><option value="">Choose customer</option>{customers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label><span>Invoice number</span><input maxLength={50} name="invoice_number" placeholder="INV-001" required /></label><label><span>Issue date</span><input name="issue_date" required type="date" /></label><label><span>Due date</span><input name="due_date" required type="date" /></label><label><span>Currency</span><select defaultValue="GBP" name="currency"><option>GBP</option><option>USD</option><option>EUR</option></select></label></div></details>
            <details className="quick-section" open><summary><span><i>02</i><strong>Line items</strong><small>{quickLines.length} item{quickLines.length === 1 ? "" : "s"} on this invoice</small></span><b>⌄</b></summary><div className="quick-lines">{quickLines.map((line) => <div className="quick-line" key={line.key}><label className="wide"><span>Description</span><input maxLength={500} onChange={(event) => updateQuickLine(line.key, "description", event.target.value)} required value={line.description} /></label><label><span>Qty</span><input min="0.001" onChange={(event) => updateQuickLine(line.key, "quantity", event.target.value)} required step="0.001" type="number" value={line.quantity} /></label><label><span>Price</span><input min="0" onChange={(event) => updateQuickLine(line.key, "unit_price", event.target.value)} required step="0.01" type="number" value={line.unit_price} /></label><label><span>VAT %</span><input max="100" min="0" onChange={(event) => updateQuickLine(line.key, "vat_rate", event.target.value)} required step="0.01" type="number" value={line.vat_rate} /></label>{quickLines.length > 1 ? <button aria-label="Remove line" onClick={() => setQuickLines((lines) => lines.filter((item) => item.key !== line.key))} type="button">×</button> : null}</div>)}<button className="quick-add-line" onClick={addQuickLine} type="button">+ Add another line</button></div></details>
            <details className="quick-section"><summary><span><i>03</i><strong>Notes</strong><small>Optional information for the customer</small></span><b>⌄</b></summary><label className="quick-notes"><textarea maxLength={5000} name="notes" placeholder="Payment terms or additional information…" rows={5} /></label></details>
            {quickError ? <p className="form-error">{quickError}</p> : null}
          </div>
          <div className="quick-action-footer"><button className="quick-cancel" onClick={closeQuickAction} type="button">Cancel</button><button className="quick-submit" disabled={quickBusy || !customers.length}>{quickBusy ? "Creating…" : "Create invoice"}</button></div>
        </form>}
      </aside>
    </div> : null}
  </div>;
}
