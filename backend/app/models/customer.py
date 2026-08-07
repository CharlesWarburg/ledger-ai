import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.user import User


class Customer(Base):
    __tablename__ = "customers"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(320),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    address_line_1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    address_line_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    country_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
    )

    vat_number: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

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

    owner: Mapped["User"] = relationship(
        back_populates="customers",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="customer",
        passive_deletes=True,
    )
