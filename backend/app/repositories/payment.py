import uuid
from datetime import date
from decimal import Decimal
from typing import Mapping, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment


def get_invoice_for_payment(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    lock: bool = False,
) -> Optional[Invoice]:
    statement = select(Invoice).where(
        Invoice.id == invoice_id,
        Invoice.owner_id == owner_id,
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def add_payment_record(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    values: Mapping[str, object],
) -> Payment:
    payment = Payment(
        owner_id=owner_id,
        invoice_id=invoice_id,
        **dict(values),
    )
    db.add(payment)
    return payment


def list_payment_records(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: Optional[uuid.UUID] = None,
    offset: int = 0,
    limit: int = 100,
    currency: Optional[str] = None,
    payment_date_from: Optional[date] = None,
    payment_date_to: Optional[date] = None,
) -> list[Payment]:
    statement = select(Payment).where(Payment.owner_id == owner_id)
    if currency is not None:
        statement = statement.join(Invoice, Invoice.id == Payment.invoice_id).where(
            Invoice.currency == currency
        )
    if invoice_id is not None:
        statement = statement.where(Payment.invoice_id == invoice_id)
    if payment_date_from is not None:
        statement = statement.where(Payment.payment_date >= payment_date_from)
    if payment_date_to is not None:
        statement = statement.where(Payment.payment_date <= payment_date_to)
    statement = (
        statement.order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_payment_record(
    db: Session,
    owner_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Optional[Payment]:
    statement = select(Payment).where(
        Payment.id == payment_id,
        Payment.owner_id == owner_id,
    )
    return db.scalar(statement)


def total_paid_for_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    exclude_payment_id: Optional[uuid.UUID] = None,
) -> Decimal:
    statement = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.owner_id == owner_id,
        Payment.invoice_id == invoice_id,
    )
    if exclude_payment_id is not None:
        statement = statement.where(Payment.id != exclude_payment_id)
    return Decimal(db.scalar(statement) or 0)


def update_payment_record(
    payment: Payment,
    values: Mapping[str, object],
) -> Payment:
    for field, value in values.items():
        setattr(payment, field, value)
    return payment


def delete_payment_record(db: Session, payment: Payment) -> None:
    db.delete(payment)
