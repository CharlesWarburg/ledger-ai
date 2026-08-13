"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { apiDownload, apiRequest, ApiError } from "@/lib/api";
import type { CashFlowForecastResponse, DashboardResponse, DuplicateInvoiceInsightsResponse, ExecutiveSummaryResponse, SlowPayerInsightsResponse } from "@/lib/api";
import { PageHeading } from "@/components/ui/page-heading";

const err = (error: unknown) => error instanceof ApiError ? error.message : "Request failed.";
const cash = (value: string | number, currency = "GBP") => new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value));

async function save(path: string, name: string, query?: Record<string, string | number>) {
  const response = await apiDownload(path, { query });
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function InsightsView() {
  const [currency, setCurrency] = useState("GBP");
  const [data, setData] = useState<{ d: DuplicateInvoiceInsightsResponse; s: SlowPayerInsightsResponse; f: CashFlowForecastResponse } | null>(null);
  const [summary, setSummary] = useState<ExecutiveSummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    Promise.all([
      apiRequest<DuplicateInvoiceInsightsResponse>("/insights/duplicates", { query: { currency } }),
      apiRequest<SlowPayerInsightsResponse>("/insights/slow-payers", { query: { currency } }),
      apiRequest<CashFlowForecastResponse>("/insights/cash-flow-forecast", { query: { currency } }),
    ]).then(([duplicates, slowPayers, forecast]) => {
      if (!cancelled) { setData({ d: duplicates, s: slowPayers, f: forecast }); setError(null); }
    }).catch((reason) => { if (!cancelled) setError(err(reason)); });
    return () => { cancelled = true; };
  }, [currency]);

  const maxForecast = Math.max(1, ...(data?.f.months.map((month) => Number(month.expected_receipts) + Number(month.overdue_receipts)) ?? []));
  const exposure = useMemo(() => data?.s.customers.reduce((sum, customer) => sum + Number(customer.overdue_balance), 0) ?? 0, [data]);
  const attentionCount = (data?.s.customers.length ?? 0) + (data?.d.matches.length ?? 0);

  async function generateSummary() {
    setSummaryLoading(true); setError(null);
    try { setSummary(await apiRequest<ExecutiveSummaryResponse>("/insights/executive-summary", { query: { currency } })); }
    catch (reason) { setError(err(reason)); }
    finally { setSummaryLoading(false); }
  }

  return <div className="intelligence-stage">
    <PageHeading actions={<label className="intelligence-currency"><span>Currency</span><select value={currency} onChange={(event) => setCurrency(event.target.value)}><option>GBP</option><option>USD</option><option>EUR</option></select></label>} title="Intelligence" description="Understand financial risk, patterns, and what needs attention." />
    {error ? <p className="form-error">{error}</p> : null}

    <section className="intelligence-briefing">
      <div className="briefing-heading"><div><span className="intelligence-kicker"><i />Executive briefing</span><h2>{summary ? "Your latest financial readout" : "Turn your ledger into a clear point of view"}</h2></div><button disabled={summaryLoading} onClick={() => void generateSummary()} type="button">{summaryLoading ? "Analysing…" : summary ? "Refresh briefing" : "Generate briefing"}</button></div>
      {summary ? <div className="briefing-content"><p>{summary.summary}</p><div className="briefing-columns"><section><span>Key findings</span>{summary.key_findings.map((item) => <p key={item}><i />{item}</p>)}</section><section className="briefing-risks"><span>Risks</span>{summary.risks.map((item) => <p key={item}><i />{item}</p>)}</section><section className="briefing-actions"><span>Recommended actions</span>{summary.recommended_actions.map((item) => <p key={item}><i />{item}</p>)}</section></div></div> : <div className="briefing-placeholder"><span>AI</span><p>Generate a concise briefing based on your invoices, balances, recent activity and forecast.</p></div>}
    </section>

    <section className="intelligence-overview">
      <article><span>Attention needed</span><strong>{attentionCount}</strong><small>Risks and possible duplicates</small></article>
      <article><span>Overdue exposure</span><strong>{cash(exposure, currency)}</strong><small>Across flagged customers</small></article>
      <article><span>Forecast horizon</span><strong>{data?.f.months.length ?? 0}</strong><small>Months of expected receipts</small></article>
    </section>

    <section className="intelligence-grid">
      <article className="intelligence-panel forecast-panel">
        <div className="intelligence-panel-heading"><div><span className="intelligence-kicker"><i />Forward view</span><h2>Cash-flow forecast</h2></div><small>Expected + overdue</small></div>
        <div className="forecast-chart">{data?.f.months.map((month) => { const expected = Number(month.expected_receipts); const overdue = Number(month.overdue_receipts); return <div className="forecast-month" key={month.month}><div className="forecast-bars" title={`${cash(expected, currency)} expected · ${cash(overdue, currency)} overdue`}><i style={{ height: `${Math.max(3, expected / maxForecast * 100)}%` }} /><b style={{ height: `${Math.max(0, overdue / maxForecast * 100)}%` }} /></div><span>{new Date(`${month.month}T00:00:00`).toLocaleDateString("en-GB", { month: "short" })}</span><small>{month.invoice_count} inv.</small></div>; })}</div>
        <div className="forecast-legend"><span><i />Expected receipts</span><span><i />Overdue exposure</span></div>
      </article>

      <article className="intelligence-panel attention-panel">
        <div className="intelligence-panel-heading"><div><span className="intelligence-kicker"><i />Priority</span><h2>Attention queue</h2></div><small>{attentionCount} items</small></div>
        <div className="attention-list">
          {data?.s.customers.slice(0, 4).map((customer) => <Link href="/invoices" key={customer.customer_id}><i className="attention-severity high" /><span><strong>{customer.customer_name}</strong><small>{customer.overdue_invoice_count} overdue · {customer.longest_days_overdue} days longest</small></span><b>{cash(customer.overdue_balance, currency)}</b></Link>)}
          {data?.d.matches.slice(0, 3).map((match, index) => <Link href="/invoices" key={`${match.first_invoice_id}-${match.second_invoice_id}`}><i className="attention-severity warning" /><span><strong>Possible duplicate · {match.customer_name}</strong><small>{match.first_invoice_number} and {match.second_invoice_number}</small></span><b>{cash(match.total, match.currency)}</b></Link>)}
          {!attentionCount ? <div className="intelligence-empty"><strong>Nothing needs attention</strong><small>No slow payers or possible duplicates were found.</small></div> : null}
        </div>
      </article>

      <article className="intelligence-panel risk-panel">
        <div className="intelligence-panel-heading"><div><span className="intelligence-kicker"><i />Customers</span><h2>Payment risk</h2></div><Link href="/customers">Customers ↗</Link></div>
        <div className="risk-grid">{data?.s.customers.length ? data.s.customers.map((customer) => { const level = customer.longest_days_overdue >= 60 ? "High" : customer.longest_days_overdue >= 30 ? "Elevated" : "Watch"; return <Link href="/invoices" key={customer.customer_id}><div><span className={`risk-level ${level.toLowerCase()}`}>{level}</span><strong>{customer.customer_name}</strong><small>{customer.overdue_invoice_count} overdue invoice{customer.overdue_invoice_count === 1 ? "" : "s"}</small></div><span><strong>{cash(customer.overdue_balance, currency)}</strong><small>{customer.longest_days_overdue} days overdue</small></span></Link>; }) : <div className="intelligence-empty"><strong>No payment risks detected</strong><small>Customers with overdue balances will appear here.</small></div>}</div>
      </article>

      <article className="intelligence-panel duplicates-panel">
        <div className="intelligence-panel-heading"><div><span className="intelligence-kicker"><i />Review</span><h2>Possible duplicates</h2></div><Link href="/invoices">Invoices ↗</Link></div>
        <div className="duplicate-list">{data?.d.matches.length ? data.d.matches.map((match, index) => <Link href="/invoices" key={`${match.first_invoice_id}-${match.second_invoice_id}`}><span className="duplicate-index">{String(index + 1).padStart(2, "0")}</span><span><strong>{match.customer_name}</strong><small>{match.first_invoice_number}</small><small>{match.second_invoice_number}</small></span><b>{cash(match.total, match.currency)}</b></Link>) : <div className="intelligence-empty"><strong>No possible duplicates</strong><small>Invoice comparisons currently look clear.</small></div>}</div>
      </article>
    </section>
  </div>;
}

export function ReportsView() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [currency, setCurrency] = useState("GBP");
  const [report, setReport] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function preview() { try { setReport(await apiRequest<DashboardResponse>("/reports/monthly", { query: { year, month, currency } })); } catch (reason) { setError(err(reason)); } }
  return <><PageHeading title="Reports" description="Preview and export your financial data." /><div className="report-controls"><input type="number" min={2000} max={2100} value={year} onChange={(event) => setYear(Number(event.target.value))} /><select value={month} onChange={(event) => setMonth(Number(event.target.value))}>{Array.from({ length: 12 }, (_, index) => <option value={index + 1} key={index}>{new Date(2020, index).toLocaleDateString("en-GB", { month: "long" })}</option>)}</select><select value={currency} onChange={(event) => setCurrency(event.target.value)}><option>GBP</option><option>USD</option><option>EUR</option></select><button className="button" onClick={preview}>Preview</button></div>{error ? <p className="form-error">{error}</p> : null}{report ? <section className="payment-summary"><article><span>Revenue</span><strong>{cash(report.kpis.total_revenue, currency)}</strong></article><article><span>Outstanding</span><strong>{cash(report.kpis.outstanding_amount, currency)}</strong></article><article><span>Overdue</span><strong>{cash(report.kpis.overdue_amount, currency)}</strong></article></section> : null}<div className="export-grid"><button onClick={() => void save("/reports/monthly.pdf", "monthly-report.pdf", { year, month, currency })}>Monthly report PDF <span>Download →</span></button><button onClick={() => void save("/reports/invoices.csv", "invoices.csv")}>Invoices CSV <span>Download →</span></button><button onClick={() => void save("/reports/payments.csv", "payments.csv")}>Payments CSV <span>Download →</span></button></div></>;
}
