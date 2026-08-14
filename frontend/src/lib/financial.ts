import type { InvoiceResponse, InvoiceStatus, PaymentResponse } from "@/lib/api";

export function paymentsByInvoice(payments: PaymentResponse[]) {
  const totals = new Map<string, number>();
  for (const payment of payments) {
    totals.set(payment.invoice_id, (totals.get(payment.invoice_id) ?? 0) + Number(payment.amount));
  }
  return totals;
}

export function invoiceBalance(invoice: InvoiceResponse, paid: number) {
  return Math.max(0, Number(invoice.total) - paid);
}

export function effectiveInvoiceStatus(
  invoice: InvoiceResponse,
  paid: number,
  today = new Date().toISOString().slice(0, 10),
): InvoiceStatus {
  if (invoice.status === "draft" || invoice.status === "cancelled") return invoice.status;
  if (invoiceBalance(invoice, paid) <= 0) return "paid";
  return invoice.due_date < today ? "overdue" : "sent";
}
