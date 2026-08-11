import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.insights import list_duplicate_invoice_candidates
from app.schemas.insights import (
    DuplicateInvoiceInsightsResponse,
    DuplicateInvoiceMatch,
)


class InsightCurrencyError(ValueError):
    pass


class InsightDateRangeError(ValueError):
    pass


def list_duplicate_invoices(
    db: Session,
    owner_id: uuid.UUID,
    currency: Optional[str] = None,
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    limit: int = 100,
) -> DuplicateInvoiceInsightsResponse:
    if issue_date_from is not None and issue_date_to is not None:
        if issue_date_to < issue_date_from:
            raise InsightDateRangeError(
                "Invoice issue-date end cannot be before its start"
            )
    normalized_currency = None
    if currency is not None:
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise InsightCurrencyError("Currency must be a three-letter code")

    candidates = list_duplicate_invoice_candidates(
        db,
        owner_id,
        currency=normalized_currency,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        limit=limit,
    )
    return DuplicateInvoiceInsightsResponse(
        matches=[
            DuplicateInvoiceMatch(
                first_invoice_id=first_invoice.id,
                first_invoice_number=first_invoice.invoice_number,
                second_invoice_id=second_invoice.id,
                second_invoice_number=second_invoice.invoice_number,
                customer_id=customer.id,
                customer_name=customer.name,
                currency=first_invoice.currency,
                total=first_invoice.total,
                issue_date=first_invoice.issue_date,
            )
            for first_invoice, second_invoice, customer in candidates
        ]
    )
