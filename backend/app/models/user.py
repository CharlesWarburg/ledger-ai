import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum, String, Uuid, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.document import Document
    from app.models.invoice import Invoice
    from app.models.payment import Payment


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
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

    customers: Mapped[list["Customer"]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner",
        passive_deletes=True,
    )
