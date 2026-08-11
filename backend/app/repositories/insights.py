import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus


def list_duplicate_invoice_candidates(
    db: Session,
    owner_id: uuid.UUID,
    currency: Optional[str] = None,
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    limit: int = 100,
) -> list[tuple[Invoice, Invoice, Customer]]:
    first_invoice = aliased(Invoice)
    second_invoice = aliased(Invoice)
    statement = (
        select(first_invoice, second_invoice, Customer)
        .join(Customer, Customer.id == first_invoice.customer_id)
        .where(
            first_invoice.owner_id == owner_id,
            second_invoice.owner_id == owner_id,
            first_invoice.id < second_invoice.id,
            first_invoice.customer_id == second_invoice.customer_id,
            first_invoice.currency == second_invoice.currency,
            first_invoice.total == second_invoice.total,
            first_invoice.issue_date == second_invoice.issue_date,
            first_invoice.status != InvoiceStatus.CANCELLED,
            second_invoice.status != InvoiceStatus.CANCELLED,
        )
        .order_by(first_invoice.issue_date.desc(), first_invoice.created_at.desc())
        .limit(limit)
    )
    if currency is not None:
        statement = statement.where(first_invoice.currency == currency)
    if issue_date_from is not None:
        statement = statement.where(first_invoice.issue_date >= issue_date_from)
    if issue_date_to is not None:
        statement = statement.where(first_invoice.issue_date <= issue_date_to)
    return list(db.execute(statement).all())
