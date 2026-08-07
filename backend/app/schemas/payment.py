import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentNormalizers(BaseModel):
    @field_validator("amount", "payment_date", mode="before", check_fields=False)
    @classmethod
    def reject_null_required_values(cls, value: object) -> object:
        if value is None:
            raise ValueError("Value cannot be null")
        return value

    @field_validator("payment_method", mode="before", check_fields=False)
    @classmethod
    def normalize_payment_method(cls, value: object) -> object:
        if value is None:
            raise ValueError("Payment method cannot be null")
        if isinstance(value, str):
            value = value.strip().lower()
            if not value:
                raise ValueError("Payment method cannot be empty")
        return value

    @field_validator("reference", "notes", mode="before", check_fields=False)
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class PaymentCreate(PaymentNormalizers):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_date: date
    payment_method: str = Field(min_length=1, max_length=50)
    reference: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class PaymentUpdate(PaymentNormalizers):
    model_config = ConfigDict(extra="forbid")

    amount: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=14,
        decimal_places=2,
    )
    payment_date: Optional[date] = None
    payment_method: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    reference: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class PaymentResponse(PaymentCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    owner_id: uuid.UUID
    invoice_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
