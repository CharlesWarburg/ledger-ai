import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment

ZERO = Decimal("0.00")


def get_revenue_total(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> Decimal:
    statement = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(
            Payment.owner_id == owner_id,
            Invoice.currency == currency,
            Payment.payment_date >= period_start,
            Payment.payment_date <= period_end,
        )
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    return Decimal(db.scalar(statement) or 0)


def get_balance_totals(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    as_of_date: date,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> tuple[Decimal, Decimal]:
    payment_totals = (
        select(
            Payment.invoice_id.label("invoice_id"),
            func.sum(Payment.amount).label("total_paid"),
        )
        .where(
            Payment.owner_id == owner_id,
            Payment.payment_date <= as_of_date,
        )
        .group_by(Payment.invoice_id)
        .subquery()
    )
    balance = func.greatest(
        Invoice.total - func.coalesce(payment_totals.c.total_paid, 0),
        0,
    )
    statement = (
        select(
            func.coalesce(func.sum(balance), 0),
            func.coalesce(
                func.sum(
                    case(
                        (Invoice.due_date < as_of_date, balance),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .outerjoin(
            payment_totals,
            payment_totals.c.invoice_id == Invoice.id,
        )
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.issue_date <= as_of_date,
            Invoice.status != InvoiceStatus.CANCELLED,
        )
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    outstanding, overdue = db.execute(statement).one()
    return Decimal(outstanding or 0), Decimal(overdue or 0)


def get_invoice_status_metrics(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> list[tuple[InvoiceStatus, int, Decimal]]:
    statement = (
        select(
            Invoice.status,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total), 0),
        )
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.issue_date >= period_start,
            Invoice.issue_date <= period_end,
        )
        .group_by(Invoice.status)
        .order_by(Invoice.status)
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    return [
        (status, int(count), Decimal(total or 0))
        for status, count, total in db.execute(statement).all()
    ]


def get_monthly_cash_flow(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> list[tuple[date, Decimal]]:
    month = func.date_trunc("month", Payment.payment_date).label("month")
    statement = (
        select(month, func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(
            Payment.owner_id == owner_id,
            Invoice.currency == currency,
            Payment.payment_date >= period_start,
            Payment.payment_date <= period_end,
        )
        .group_by(month)
        .order_by(month)
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    return [
        (month_value.date(), Decimal(amount or 0))
        for month_value, amount in db.execute(statement).all()
    ]


def list_recent_invoice_activity(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    limit: int = 10,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> list[Invoice]:
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(period_end, time.max, tzinfo=timezone.utc)
    statement = (
        select(Invoice)
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.created_at >= start_at,
            Invoice.created_at <= end_at,
        )
        .order_by(Invoice.created_at.desc())
        .limit(limit)
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    return list(db.scalars(statement).all())


def list_recent_payment_activity(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    period_start: date,
    period_end: date,
    limit: int = 10,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> list[Payment]:
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(period_end, time.max, tzinfo=timezone.utc)
    statement = (
        select(Payment)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(
            Payment.owner_id == owner_id,
            Invoice.currency == currency,
            Payment.created_at >= start_at,
            Payment.created_at <= end_at,
        )
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    if invoice_status is not None:
        statement = statement.where(Invoice.status == invoice_status)
    if customer_id is not None:
        statement = statement.where(Invoice.customer_id == customer_id)
    return list(db.scalars(statement).all())
