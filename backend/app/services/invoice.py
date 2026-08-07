import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.customer import get_customer_record
from app.repositories.invoice import (
    add_invoice_record,
    delete_invoice_record,
    get_invoice_record,
    invoice_number_exists,
    list_invoice_records,
    replace_invoice_line_items,
    update_invoice_record,
)
from app.schemas.invoice import InvoiceCreate, InvoiceLineItemCreate, InvoiceUpdate

MONEY_QUANTUM = Decimal("0.01")
ONE_HUNDRED = Decimal("100")


class InvoiceNotFoundError(ValueError):
    pass


class InvoiceCustomerNotFoundError(ValueError):
    pass


class InvoiceNumberAlreadyExistsError(ValueError):
    pass


class InvoiceDateError(ValueError):
    pass


class InvalidInvoiceStatusTransitionError(ValueError):
    pass


class InvoiceFilterDateError(ValueError):
    pass


ALLOWED_STATUS_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.DRAFT: {InvoiceStatus.SENT, InvoiceStatus.CANCELLED},
    InvoiceStatus.SENT: {
        InvoiceStatus.PAID,
        InvoiceStatus.OVERDUE,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.OVERDUE: {
        InvoiceStatus.PAID,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.PAID: set(),
    InvoiceStatus.CANCELLED: set(),
}


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_invoice_values(
    line_items: Sequence[InvoiceLineItemCreate],
) -> tuple[list[dict[str, object]], Decimal, Decimal, Decimal]:
    calculated_lines: list[dict[str, object]] = []
    subtotal = Decimal("0.00")
    vat_total = Decimal("0.00")

    for position, line_item in enumerate(line_items):
        line_subtotal = _round_money(line_item.quantity * line_item.unit_price)
        vat_amount = _round_money(
            line_subtotal * line_item.vat_rate / ONE_HUNDRED
        )
        line_total = line_subtotal + vat_amount
        subtotal += line_subtotal
        vat_total += vat_amount
        calculated_lines.append(
            {
                **line_item.model_dump(),
                "subtotal": line_subtotal,
                "vat_amount": vat_amount,
                "total": line_total,
                "position": position,
            }
        )

    subtotal = _round_money(subtotal)
    vat_total = _round_money(vat_total)
    total = subtotal + vat_total
    return calculated_lines, subtotal, vat_total, total


def _require_owned_customer(
    db: Session,
    owner_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> None:
    if get_customer_record(db, owner_id, customer_id) is None:
        raise InvoiceCustomerNotFoundError("Customer not found")


def _validate_dates(issue_date: date, due_date: date) -> None:
    if due_date < issue_date:
        raise InvoiceDateError("Due date cannot be before issue date")


def _commit_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_number: str,
    exclude_invoice_id: Optional[uuid.UUID] = None,
) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if invoice_number_exists(
            db,
            owner_id,
            invoice_number,
            exclude_invoice_id=exclude_invoice_id,
        ):
            raise InvoiceNumberAlreadyExistsError(
                "Invoice number is already in use"
            ) from exc
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def create_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_data: InvoiceCreate,
) -> Invoice:
    _require_owned_customer(db, owner_id, invoice_data.customer_id)
    if invoice_number_exists(db, owner_id, invoice_data.invoice_number):
        raise InvoiceNumberAlreadyExistsError("Invoice number is already in use")

    calculated_lines, subtotal, vat_total, total = calculate_invoice_values(
        invoice_data.line_items
    )
    invoice_values = invoice_data.model_dump(exclude={"line_items"})
    invoice_values.update(
        {
            "subtotal": subtotal,
            "vat_total": vat_total,
            "total": total,
        }
    )
    invoice = add_invoice_record(
        db,
        owner_id,
        invoice_values,
        calculated_lines,
    )
    _commit_invoice(db, owner_id, invoice_data.invoice_number)
    db.refresh(invoice)
    return invoice


def list_invoices(
    db: Session,
    owner_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
    status: Optional[InvoiceStatus] = None,
    currency: Optional[str] = None,
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    has_balance: Optional[bool] = None,
    overdue_only: bool = False,
) -> list[Invoice]:
    if (
        issue_date_from is not None
        and issue_date_to is not None
        and issue_date_to < issue_date_from
    ):
        raise InvoiceFilterDateError(
            "Invoice issue-date end cannot be before its start"
        )
    normalized_currency = currency.strip().upper() if currency else None
    return list_invoice_records(
        db,
        owner_id,
        offset=offset,
        limit=limit,
        status=status,
        currency=normalized_currency,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        has_balance=has_balance,
        overdue_only=overdue_only,
    )


def get_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice:
    invoice = get_invoice_record(db, owner_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError("Invoice not found")
    return invoice


def update_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    invoice_data: InvoiceUpdate,
) -> Invoice:
    invoice = get_invoice(db, owner_id, invoice_id)
    line_items = (
        invoice_data.line_items
        if "line_items" in invoice_data.model_fields_set
        else None
    )
    values = invoice_data.model_dump(exclude_unset=True, exclude={"line_items"})

    customer_id = values.get("customer_id", invoice.customer_id)
    if customer_id != invoice.customer_id:
        _require_owned_customer(db, owner_id, customer_id)

    invoice_number = values.get("invoice_number", invoice.invoice_number)
    if invoice_number != invoice.invoice_number and invoice_number_exists(
        db,
        owner_id,
        invoice_number,
        exclude_invoice_id=invoice.id,
    ):
        raise InvoiceNumberAlreadyExistsError("Invoice number is already in use")

    issue_date = values.get("issue_date", invoice.issue_date)
    due_date = values.get("due_date", invoice.due_date)
    _validate_dates(issue_date, due_date)

    if line_items is not None:
        calculated_lines, subtotal, vat_total, total = calculate_invoice_values(
            line_items
        )
        values.update(
            {
                "subtotal": subtotal,
                "vat_total": vat_total,
                "total": total,
            }
        )
        try:
            replace_invoice_line_items(db, invoice, calculated_lines)
        except SQLAlchemyError:
            db.rollback()
            raise

    update_invoice_record(invoice, values)
    _commit_invoice(
        db,
        owner_id,
        invoice_number,
        exclude_invoice_id=invoice.id,
    )
    db.refresh(invoice)
    return invoice


def update_invoice_status(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
    new_status: InvoiceStatus,
) -> Invoice:
    invoice = get_invoice(db, owner_id, invoice_id)
    if new_status == invoice.status:
        return invoice
    if new_status not in ALLOWED_STATUS_TRANSITIONS[invoice.status]:
        raise InvalidInvoiceStatusTransitionError(
            f"Cannot change invoice status from "
            f"{invoice.status.value} to {new_status.value}"
        )

    update_invoice_record(invoice, {"status": new_status})
    _commit_invoice(
        db,
        owner_id,
        invoice.invoice_number,
        exclude_invoice_id=invoice.id,
    )
    db.refresh(invoice)
    return invoice


def delete_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> None:
    invoice = get_invoice(db, owner_id, invoice_id)
    delete_invoice_record(db, invoice)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
