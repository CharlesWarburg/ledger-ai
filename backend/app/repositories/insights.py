import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment


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


def list_outstanding_invoice_balances(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    as_of_date: date,
    due_date_to: date,
) -> list[tuple[date, Decimal]]:
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
    balance = Invoice.total - func.coalesce(payment_totals.c.total_paid, 0)
    statement = (
        select(Invoice.due_date, balance)
        .outerjoin(payment_totals, payment_totals.c.invoice_id == Invoice.id)
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.issue_date <= as_of_date,
            Invoice.due_date <= due_date_to,
            Invoice.status != InvoiceStatus.CANCELLED,
            balance > 0,
        )
        .order_by(Invoice.due_date)
    )
    return [
        (due_date, Decimal(amount))
        for due_date, amount in db.execute(statement).all()
    ]


def list_overdue_invoice_balances(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    as_of_date: date,
) -> list[tuple[Customer, date, Decimal]]:
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
    balance = Invoice.total - func.coalesce(payment_totals.c.total_paid, 0)
    statement = (
        select(Customer, Invoice.due_date, balance)
        .join(Customer, Customer.id == Invoice.customer_id)
        .outerjoin(payment_totals, payment_totals.c.invoice_id == Invoice.id)
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.issue_date <= as_of_date,
            Invoice.due_date < as_of_date,
            Invoice.status != InvoiceStatus.CANCELLED,
            balance > 0,
        )
        .order_by(Invoice.due_date)
    )
    return [
        (customer, due_date, Decimal(amount))
        for customer, due_date, amount in db.execute(statement).all()
    ]


def list_customer_outstanding_balances(
    db: Session,
    owner_id: uuid.UUID,
    currency: str,
    as_of_date: date,
) -> list[tuple[Customer, int, Decimal]]:
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
    balance = Invoice.total - func.coalesce(payment_totals.c.total_paid, 0)
    statement = (
        select(
            Customer,
            func.count(Invoice.id),
            func.sum(balance).label("outstanding_balance"),
        )
        .join(Customer, Customer.id == Invoice.customer_id)
        .outerjoin(payment_totals, payment_totals.c.invoice_id == Invoice.id)
        .where(
            Invoice.owner_id == owner_id,
            Invoice.currency == currency,
            Invoice.issue_date <= as_of_date,
            Invoice.status != InvoiceStatus.CANCELLED,
            balance > 0,
        )
        .group_by(Customer.id)
        .order_by(func.sum(balance).desc(), Customer.name)
    )
    return [
        (customer, int(invoice_count), Decimal(outstanding_balance))
        for customer, invoice_count, outstanding_balance in db.execute(statement).all()
    ]
