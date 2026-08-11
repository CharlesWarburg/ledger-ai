import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.invoice import InvoiceStatus
from app.models.user import User
from app.services.invoice import list_invoices
from app.services.payment import list_all_payments

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/invoices.csv")
def export_invoices_csv(
    currency: Optional[str] = Query(default=None, min_length=3, max_length=3),
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    invoices = list_invoices(
        db, current_user.id, limit=1000, currency=currency,
        issue_date_from=issue_date_from, issue_date_to=issue_date_to,
        status=invoice_status,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["invoice_number", "customer_id", "status", "currency", "issue_date", "due_date", "subtotal", "vat_total", "total"])
    for invoice in invoices:
        writer.writerow([invoice.invoice_number, invoice.customer_id, invoice.status.value, invoice.currency, invoice.issue_date, invoice.due_date, invoice.subtotal, invoice.vat_total, invoice.total])
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"},
    )


@router.get("/payments.csv")
def export_payments_csv(
    payment_date_from: Optional[date] = None,
    payment_date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    payments = list_all_payments(
        db, current_user.id, limit=1000,
        payment_date_from=payment_date_from, payment_date_to=payment_date_to,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["invoice_id", "amount", "payment_date", "reference", "notes"])
    for payment in payments:
        writer.writerow([payment.invoice_id, payment.amount, payment.payment_date, payment.reference or "", payment.notes or ""])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=payments.csv"})
