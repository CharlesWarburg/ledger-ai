import uuid
from typing import Mapping, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.invoice import Invoice, InvoiceLineItem


def invoice_number_exists(
    db: Session,
    owner_id: uuid.UUID,
    invoice_number: str,
    exclude_invoice_id: Optional[uuid.UUID] = None,
) -> bool:
    statement = select(Invoice.id).where(
        Invoice.owner_id == owner_id,
        Invoice.invoice_number == invoice_number,
    )
    if exclude_invoice_id is not None:
        statement = statement.where(Invoice.id != exclude_invoice_id)
    return db.scalar(statement) is not None


def add_invoice_record(
    db: Session,
    owner_id: uuid.UUID,
    invoice_values: Mapping[str, object],
    line_item_values: Sequence[Mapping[str, object]],
) -> Invoice:
    invoice = Invoice(
        owner_id=owner_id,
        **dict(invoice_values),
        line_items=[
            InvoiceLineItem(**dict(line_values))
            for line_values in line_item_values
        ],
    )
    db.add(invoice)
    return invoice


def list_invoice_records(
    db: Session,
    owner_id: uuid.UUID,
    offset: int = 0,
    limit: int = 100,
) -> list[Invoice]:
    statement = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.owner_id == owner_id)
        .order_by(Invoice.issue_date.desc(), Invoice.invoice_number.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_invoice_record(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Optional[Invoice]:
    statement = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(
            Invoice.id == invoice_id,
            Invoice.owner_id == owner_id,
        )
    )
    return db.scalar(statement)


def update_invoice_record(
    invoice: Invoice,
    values: Mapping[str, object],
) -> Invoice:
    for field, value in values.items():
        setattr(invoice, field, value)
    return invoice


def replace_invoice_line_items(
    db: Session,
    invoice: Invoice,
    line_item_values: Sequence[Mapping[str, object]],
) -> Invoice:
    for line_item in list(invoice.line_items):
        db.delete(line_item)
    db.flush()
    invoice.line_items = [
        InvoiceLineItem(**dict(line_values))
        for line_values in line_item_values
    ]
    return invoice


def delete_invoice_record(db: Session, invoice: Invoice) -> None:
    db.delete(invoice)
