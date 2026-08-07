import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.document import Document
    from app.models.payment import Payment
    from app.models.user import User


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "invoice_number",
            name="uq_invoices_owner_invoice_number",
        ),
        CheckConstraint(
            "due_date >= issue_date",
            name="ck_invoices_due_date_not_before_issue_date",
        ),
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonnegative"),
        CheckConstraint("vat_total >= 0", name="ck_invoices_vat_nonnegative"),
        CheckConstraint(
            "total = subtotal + vat_total",
            name="ck_invoices_total_matches_components",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=InvoiceStatus.DRAFT,
        server_default=InvoiceStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="GBP",
        server_default="GBP",
        nullable=False,
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        server_default="0",
        nullable=False,
    )
    vat_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        server_default="0",
        nullable=False,
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0.00"),
        server_default="0",
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="invoices")
    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="InvoiceLineItem.position",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice",
        passive_deletes=True,
        order_by="Payment.payment_date",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="invoice",
        passive_deletes=True,
        order_by="Document.created_at",
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (
        UniqueConstraint(
            "invoice_id",
            "position",
            name="uq_invoice_line_items_invoice_position",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_invoice_line_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_invoice_line_items_unit_price_nonnegative",
        ),
        CheckConstraint(
            "vat_rate >= 0 AND vat_rate <= 100",
            name="ck_invoice_line_items_vat_rate_range",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_invoice_line_items_subtotal_nonnegative",
        ),
        CheckConstraint(
            "vat_amount >= 0",
            name="ck_invoice_line_items_vat_amount_nonnegative",
        ),
        CheckConstraint(
            "total = subtotal + vat_amount",
            name="ck_invoice_line_items_total_matches_components",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_invoice_line_items_position_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")
