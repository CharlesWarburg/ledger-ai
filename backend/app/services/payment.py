import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.repositories.payment import (
    add_payment_record,
    delete_payment_record,
    get_invoice_for_payment,
    get_payment_record,
    list_payment_records,
    total_paid_for_invoice,
    update_payment_record,
)
from app.schemas.payment import PaymentCreate, PaymentUpdate

ZERO = Decimal("0.00")
PAYABLE_INVOICE_STATUSES = {InvoiceStatus.SENT, InvoiceStatus.OVERDUE}


class PaymentNotFoundError(ValueError):
    pass


class PaymentInvoiceNotFoundError(ValueError):
    pass


class PaymentInvoiceStatusError(ValueError):
    pass


class PaymentExceedsOutstandingBalanceError(ValueError):
    pass


class PaymentDateError(ValueError):
    pass


def _require_owned_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    lock: bool = False,
) -> Invoice:
    invoice = get_invoice_for_payment(
        db,
        owner_id,
        invoice_id,
        lock=lock,
    )
    if invoice is None:
        raise PaymentInvoiceNotFoundError("Invoice not found")
    return invoice


def _validate_payment_date(payment_date: date, invoice: Invoice) -> None:
    if payment_date < invoice.issue_date:
        raise PaymentDateError("Payment date cannot be before invoice issue date")
    if payment_date > date.today():
        raise PaymentDateError("Payment date cannot be in the future")


def _outstanding_balance(
    db: Session,
    owner_id: uuid.UUID,
    invoice: Invoice,
    exclude_payment_id: Optional[uuid.UUID] = None,
) -> Decimal:
    total_paid = total_paid_for_invoice(
        db,
        owner_id,
        invoice.id,
        exclude_payment_id=exclude_payment_id,
    )
    return max(invoice.total - total_paid, ZERO)


def _sync_invoice_status(invoice: Invoice, outstanding_balance: Decimal) -> None:
    if outstanding_balance == ZERO and invoice.status != InvoiceStatus.CANCELLED:
        invoice.status = InvoiceStatus.PAID
    elif outstanding_balance > ZERO and invoice.status == InvoiceStatus.PAID:
        invoice.status = (
            InvoiceStatus.OVERDUE
            if invoice.due_date < date.today()
            else InvoiceStatus.SENT
        )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def create_payment(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_data: PaymentCreate,
) -> Payment:
    invoice = _require_owned_invoice(db, owner_id, invoice_id, lock=True)
    if invoice.status not in PAYABLE_INVOICE_STATUSES:
        raise PaymentInvoiceStatusError(
            "Payments can only be recorded for sent or overdue invoices"
        )
    _validate_payment_date(payment_data.payment_date, invoice)

    outstanding_balance = _outstanding_balance(db, owner_id, invoice)
    if payment_data.amount > outstanding_balance:
        raise PaymentExceedsOutstandingBalanceError(
            "Payment amount exceeds the outstanding balance"
        )

    payment = add_payment_record(
        db,
        owner_id,
        invoice_id,
        payment_data.model_dump(),
    )
    _sync_invoice_status(invoice, outstanding_balance - payment_data.amount)
    _commit(db)
    db.refresh(payment)
    return payment


def list_payments(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
) -> list[Payment]:
    _require_owned_invoice(db, owner_id, invoice_id)
    return list_payment_records(
        db,
        owner_id,
        invoice_id,
        offset=offset,
        limit=limit,
    )


def get_payment(
    db: Session,
    owner_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Payment:
    payment = get_payment_record(db, owner_id, payment_id)
    if payment is None:
        raise PaymentNotFoundError("Payment not found")
    return payment


def get_outstanding_balance(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Decimal:
    invoice = _require_owned_invoice(db, owner_id, invoice_id)
    return _outstanding_balance(db, owner_id, invoice)


def update_payment(
    db: Session,
    owner_id: uuid.UUID,
    payment_id: uuid.UUID,
    payment_data: PaymentUpdate,
) -> Payment:
    payment = get_payment(db, owner_id, payment_id)
    invoice = _require_owned_invoice(
        db,
        owner_id,
        payment.invoice_id,
        lock=True,
    )
    values = payment_data.model_dump(exclude_unset=True)

    payment_date = values.get("payment_date", payment.payment_date)
    _validate_payment_date(payment_date, invoice)

    amount = values.get("amount", payment.amount)
    available_balance = _outstanding_balance(
        db,
        owner_id,
        invoice,
        exclude_payment_id=payment.id,
    )
    if amount > available_balance:
        raise PaymentExceedsOutstandingBalanceError(
            "Payment amount exceeds the outstanding balance"
        )

    update_payment_record(payment, values)
    _sync_invoice_status(invoice, available_balance - amount)
    _commit(db)
    db.refresh(payment)
    return payment


def delete_payment(
    db: Session,
    owner_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> None:
    payment = get_payment(db, owner_id, payment_id)
    invoice = _require_owned_invoice(
        db,
        owner_id,
        payment.invoice_id,
        lock=True,
    )
    outstanding_after_delete = _outstanding_balance(
        db,
        owner_id,
        invoice,
        exclude_payment_id=payment.id,
    )
    delete_payment_record(db, payment)
    _sync_invoice_status(invoice, outstanding_after_delete)
    _commit(db)
