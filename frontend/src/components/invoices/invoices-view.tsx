"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest, ApiError } from "@/lib/api";
import type { CustomerResponse, InvoiceCreate, InvoiceLineItemCreate, InvoiceResponse, InvoiceStatus, PaymentResponse } from "@/lib/api";
import { effectiveInvoiceStatus, invoiceBalance, paymentsByInvoice } from "@/lib/financial";
import { PageHeading } from "@/components/ui/page-heading";

type Mode = "view" | "edit" | "create";
type LineDraft = InvoiceLineItemCreate & { key: number };

const transitions: Record<InvoiceStatus, InvoiceStatus[]> = {
  draft: ["sent", "cancelled"], sent: ["cancelled"], overdue: ["cancelled"], paid: [], cancelled: [],
};
const statusLabels: Record<InvoiceStatus, string> = { draft: "Draft", sent: "Sent", paid: "Paid", overdue: "Overdue", cancelled: "Cancelled" };
const blankLine = (key: number): LineDraft => ({ key, description: "", quantity: "1", unit_price: "0", vat_rate: "20" });
const today = () => new Date().toISOString().slice(0, 10);

function messageFrom(error: unknown) { return error instanceof ApiError ? error.message : "Unable to complete this request."; }
function money(value: string | number, currency = "GBP") { return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(Number(value)); }
function round(value: number) { return Math.round((value + Number.EPSILON) * 100) / 100; }
function lineValues(line: LineDraft) { const subtotal = round(Number(line.quantity || 0) * Number(line.unit_price || 0)); const vat = round(subtotal * Number(line.vat_rate || 0) / 100); return { subtotal, vat, total: subtotal + vat }; }

export function InvoicesView() {
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [payments, setPayments] = useState<PaymentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<InvoiceStatus | "all">("all");
  const [selected, setSelected] = useState<InvoiceResponse | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [lines, setLines] = useState<LineDraft[]>([blankLine(1)]);
  const [nextKey, setNextKey] = useState(2);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  function load() {
    setLoading(true); setLoadError(null);
    Promise.all([
      apiRequest<InvoiceResponse[]>("/invoices", { query: { limit: 100 } }),
      apiRequest<CustomerResponse[]>("/customers", { query: { limit: 100 } }),
      apiRequest<PaymentResponse[]>("/payments", { query: { limit: 100 } }),
    ]).then(([invoiceData, customerData, paymentData]) => { setInvoices(invoiceData); setCustomers(customerData); setPayments(paymentData); })
      .catch((error: unknown) => setLoadError(messageFrom(error))).finally(() => setLoading(false));
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([apiRequest<InvoiceResponse[]>("/invoices", { query: { limit: 100 } }), apiRequest<CustomerResponse[]>("/customers", { query: { limit: 100 } }), apiRequest<PaymentResponse[]>("/payments", { query: { limit: 100 } })])
      .then(([invoiceData, customerData, paymentData]) => { if (!cancelled) { setInvoices(invoiceData); setCustomers(customerData); setPayments(paymentData); } })
      .catch((error: unknown) => { if (!cancelled) setLoadError(messageFrom(error)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const customerById = useMemo(() => new Map(customers.map((customer) => [customer.id, customer])), [customers]);
  const paidByInvoice = useMemo(() => paymentsByInvoice(payments), [payments]);
  const displayStatus = (invoice: InvoiceResponse) => effectiveInvoiceStatus(invoice, paidByInvoice.get(invoice.id) ?? 0);
  const visible = useMemo(() => invoices.filter((invoice) => {
    const needle = query.trim().toLowerCase();
    const customer = customerById.get(invoice.customer_id)?.name ?? "";
    return (status === "all" || effectiveInvoiceStatus(invoice, paidByInvoice.get(invoice.id) ?? 0) === status) && (!needle || invoice.invoice_number.toLowerCase().includes(needle) || customer.toLowerCase().includes(needle));
  }), [invoices, query, status, customerById, paidByInvoice]);
  const totals = lines.reduce((sum, line) => { const value = lineValues(line); return { subtotal: sum.subtotal + value.subtotal, vat: sum.vat + value.vat, total: sum.total + value.total }; }, { subtotal: 0, vat: 0, total: 0 });

  function openCreate() { setSelected(null); setLines([blankLine(1)]); setNextKey(2); setMode("create"); setFormError(null); setConfirmDelete(false); }
  function openInvoice(invoice: InvoiceResponse, nextMode: Mode = "view") {
    setSelected(invoice); setLines(invoice.line_items.map((line, index) => ({ key: index + 1, description: line.description, quantity: line.quantity, unit_price: line.unit_price, vat_rate: line.vat_rate })));
    setNextKey(invoice.line_items.length + 1); setMode(nextMode); setFormError(null); setConfirmDelete(false);
  }
  function close() { if (!saving) { setMode(null); setSelected(null); } }
  function updateLine(key: number, field: keyof InvoiceLineItemCreate, value: string) { setLines((current) => current.map((line) => line.key === key ? { ...line, [field]: value } : line)); }
  function addLine() { setLines((current) => [...current, blankLine(nextKey)]); setNextKey((value) => value + 1); }
  function removeLine(key: number) { if (lines.length > 1) setLines((current) => current.filter((line) => line.key !== key)); }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setFormError(null);
    const data = new FormData(event.currentTarget);
    const payload: InvoiceCreate = {
      customer_id: String(data.get("customer_id")), invoice_number: String(data.get("invoice_number")).trim(), currency: String(data.get("currency")).trim().toUpperCase(),
      issue_date: String(data.get("issue_date")), due_date: String(data.get("due_date")), notes: String(data.get("notes") ?? "").trim() || null,
      line_items: lines.map(({ description, quantity, unit_price, vat_rate }) => ({ description: description.trim(), quantity, unit_price, vat_rate })),
    };
    try {
      const saved = selected
        ? await apiRequest<InvoiceResponse>(`/invoices/${selected.id}`, { method: "PATCH", body: payload })
        : await apiRequest<InvoiceResponse>("/invoices", { method: "POST", body: payload });
      setInvoices((current) => selected ? current.map((invoice) => invoice.id === saved.id ? saved : invoice) : [saved, ...current]);
      openInvoice(saved);
    } catch (error) { setFormError(messageFrom(error)); } finally { setSaving(false); }
  }

  async function changeStatus(nextStatus: InvoiceStatus) {
    if (!selected) return; setSaving(true); setFormError(null);
    try { const updated = await apiRequest<InvoiceResponse>(`/invoices/${selected.id}/status`, { method: "PATCH", body: { status: nextStatus } }); setInvoices((current) => current.map((invoice) => invoice.id === updated.id ? updated : invoice)); openInvoice(updated); }
    catch (error) { setFormError(messageFrom(error)); } finally { setSaving(false); }
  }

  async function deleteInvoice() {
    if (!selected) return; setSaving(true); setFormError(null);
    try { await apiRequest<void>(`/invoices/${selected.id}`, { method: "DELETE" }); setInvoices((current) => current.filter((invoice) => invoice.id !== selected.id)); close(); }
    catch (error) { setFormError(messageFrom(error)); } finally { setSaving(false); }
  }

  return <div className="invoices-stage">
    <PageHeading actions={<button className="button" disabled={!customers.length} onClick={openCreate} type="button">Create invoice</button>} description="Create, send, and track every invoice." title="Invoices" />
    {!customers.length && !loading ? <div className="inline-notice">Add a customer before creating an invoice.</div> : null}
    <div className="invoice-toolbar">
      <label className="search-field"><span aria-hidden="true">⌕</span><span className="sr-only">Search invoices</span><input onChange={(event) => setQuery(event.target.value)} placeholder="Search invoice or customer" type="search" value={query} /></label>
      <div className="status-filters">{(["all", "draft", "sent", "overdue", "paid", "cancelled"] as const).map((value) => <button className={status === value ? "active" : ""} key={value} onClick={() => setStatus(value)} type="button">{value === "all" ? "All" : statusLabels[value]}</button>)}</div>
    </div>
    {loading ? <div className="customer-list loading-list" role="status">{[1,2,3,4].map((value) => <div className="customer-row skeleton-row" key={value} />)}</div>
    : loadError ? <div className="state-card error-state"><div className="state-icon">!</div><h2>Invoices couldn’t load</h2><p>{loadError}</p><button className="button" onClick={load} type="button">Try again</button></div>
    : invoices.length === 0 ? <div className="state-card"><div className="state-icon">+</div><h2>Create your first invoice</h2><p>Add line items, VAT, dates, and customer details in one place.</p>{customers.length ? <button className="button" onClick={openCreate} type="button">Create invoice</button> : null}</div>
    : visible.length === 0 ? <div className="state-card small-state"><div className="state-icon">⌕</div><h2>No matching invoices</h2><p>Adjust your search or status filter.</p></div>
    : <div className="invoice-list"><div className="invoice-list-head"><span>Invoice</span><span>Customer</span><span>Issued</span><span>Due</span><span>Status</span><span>Total</span><span /></div>{visible.map((invoice) => { const currentStatus = displayStatus(invoice); return <button className="invoice-row" key={invoice.id} onClick={() => openInvoice(invoice)} type="button"><strong>{invoice.invoice_number}</strong><span>{customerById.get(invoice.customer_id)?.name ?? "Unknown customer"}</span><span>{invoice.issue_date}</span><span>{invoice.due_date}</span><span><i className={`status-badge ${currentStatus}`}>{statusLabels[currentStatus]}</i></span><strong>{money(invoice.total, invoice.currency)}</strong><span className="row-arrow">›</span></button>; })}</div>}

    {mode ? <div className="drawer-layer"><button aria-label="Close invoice panel" className="drawer-backdrop" disabled={saving} onClick={close} type="button" /><aside aria-modal="true" className="invoice-drawer" role="dialog">
      <div className="drawer-heading"><div><span className="kicker">{mode === "create" ? "New invoice" : mode === "edit" ? "Edit invoice" : "Invoice details"}</span><h2>{mode === "create" ? "Create invoice" : selected?.invoice_number}</h2></div><button aria-label="Close" className="icon-button" onClick={close} type="button">×</button></div>
      {mode === "view" && selected ? <div className="invoice-detail">
        <div className="invoice-detail-top"><div><span>Bill to</span><strong>{customerById.get(selected.customer_id)?.name}</strong><small>{customerById.get(selected.customer_id)?.email ?? "No email"}</small></div><i className={`status-badge ${displayStatus(selected)}`}>{statusLabels[displayStatus(selected)]}</i></div>
        <div className="invoice-meta"><div><span>Issued</span><strong>{selected.issue_date}</strong></div><div><span>Due</span><strong>{selected.due_date}</strong></div><div><span>Currency</span><strong>{selected.currency}</strong></div></div>
        <div className="detail-lines">{selected.line_items.map((line) => <div key={line.id}><span><strong>{line.description}</strong><small>{line.quantity} × {money(line.unit_price, selected.currency)} · {line.vat_rate}% VAT</small></span><strong>{money(line.total, selected.currency)}</strong></div>)}</div>
        <div className="invoice-totals"><span>Subtotal <strong>{money(selected.subtotal, selected.currency)}</strong></span><span>VAT <strong>{money(selected.vat_total, selected.currency)}</strong></span><span>Paid <strong>{money(paidByInvoice.get(selected.id) ?? 0, selected.currency)}</strong></span><span className="grand-total">Balance due <strong>{money(invoiceBalance(selected, paidByInvoice.get(selected.id) ?? 0), selected.currency)}</strong></span></div>
        {selected.notes ? <div className="invoice-notes"><span>Notes</span><p>{selected.notes}</p></div> : null}
        {formError ? <p className="form-error">{formError}</p> : null}
        {confirmDelete ? <div className="delete-confirm"><p>Delete invoice <strong>{selected.invoice_number}</strong>?</p><div><button className="text-button" onClick={() => setConfirmDelete(false)} type="button">Cancel</button><button className="danger-button" disabled={saving} onClick={() => void deleteInvoice()} type="button">Delete invoice</button></div></div> : null}
        <div className="detail-actions"><button className="text-button danger-text" onClick={() => setConfirmDelete(true)} type="button">Delete</button><div>{transitions[selected.status].map((next) => <button className="button secondary" disabled={saving} key={next} onClick={() => void changeStatus(next)} type="button">Mark {statusLabels[next]}</button>)}<button className="button" onClick={() => openInvoice(selected, "edit")} type="button">Edit</button></div></div>
      </div> : <form className="invoice-form" onSubmit={submit}>
        <div className="form-section"><h3>Invoice details</h3><div className="form-grid"><label className="form-control"><span>Customer *</span><select defaultValue={selected?.customer_id ?? ""} name="customer_id" required><option disabled value="">Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label><label className="form-control"><span>Invoice number *</span><input defaultValue={selected?.invoice_number ?? ""} maxLength={50} name="invoice_number" required /></label><label className="form-control"><span>Issue date *</span><input defaultValue={selected?.issue_date ?? today()} name="issue_date" required type="date" /></label><label className="form-control"><span>Due date *</span><input defaultValue={selected?.due_date ?? today()} name="due_date" required type="date" /></label><label className="form-control"><span>Currency *</span><input defaultValue={selected?.currency ?? "GBP"} maxLength={3} minLength={3} name="currency" required /></label></div></div>
        <div className="form-section"><div className="line-heading"><h3>Line items</h3><button className="text-button" onClick={addLine} type="button">+ Add line</button></div><div className="line-items">{lines.map((line) => { const values = lineValues(line); return <div className="line-item" key={line.key}><label className="form-control line-description"><span>Description *</span><input maxLength={500} onChange={(event) => updateLine(line.key, "description", event.target.value)} required value={line.description} /></label><label className="form-control"><span>Quantity</span><input min="0.001" onChange={(event) => updateLine(line.key, "quantity", event.target.value)} required step="0.001" type="number" value={line.quantity} /></label><label className="form-control"><span>Unit price</span><input min="0" onChange={(event) => updateLine(line.key, "unit_price", event.target.value)} required step="0.0001" type="number" value={line.unit_price} /></label><label className="form-control"><span>VAT %</span><input max="100" min="0" onChange={(event) => updateLine(line.key, "vat_rate", event.target.value)} required step="0.01" type="number" value={line.vat_rate} /></label><strong className="line-total">{money(values.total, selected?.currency ?? "GBP")}</strong><button aria-label="Remove line" className="remove-line" disabled={lines.length === 1} onClick={() => removeLine(line.key)} type="button">×</button></div>; })}</div><div className="invoice-totals preview"><span>Subtotal <strong>{money(totals.subtotal, selected?.currency ?? "GBP")}</strong></span><span>VAT <strong>{money(totals.vat, selected?.currency ?? "GBP")}</strong></span><span className="grand-total">Total <strong>{money(totals.total, selected?.currency ?? "GBP")}</strong></span></div></div>
        <div className="form-section"><label className="form-control"><span>Notes</span><textarea defaultValue={selected?.notes ?? ""} maxLength={5000} name="notes" rows={4} /></label></div>{formError ? <p className="form-error">{formError}</p> : null}<div className="drawer-actions"><span /><div><button className="button secondary" onClick={selected ? () => openInvoice(selected) : close} type="button">Cancel</button><button className="button" disabled={saving} type="submit">{saving ? "Saving…" : selected ? "Save changes" : "Create invoice"}</button></div></div>
      </form>}
    </aside></div> : null}
  </div>;
}
