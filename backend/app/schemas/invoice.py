import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.invoice import InvoiceStatus


class InvoiceLineItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    vat_rate: Decimal = Field(
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Line item description cannot be empty")
        return value


class InvoiceLineItemResponse(InvoiceLineItemCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    invoice_id: uuid.UUID
    subtotal: Decimal
    vat_amount: Decimal
    total: Decimal
    position: int


class InvoiceNormalizers(BaseModel):
    @field_validator("invoice_number", mode="before", check_fields=False)
    @classmethod
    def normalize_invoice_number(cls, value: object) -> object:
        if value is None:
            raise ValueError("Invoice number cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Invoice number cannot be empty")
        return value

    @field_validator("currency", mode="before", check_fields=False)
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if value is None:
            raise ValueError("Currency cannot be null")
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("notes", mode="before", check_fields=False)
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class InvoiceCreate(InvoiceNormalizers):
    model_config = ConfigDict(extra="forbid")

    customer_id: uuid.UUID
    invoice_number: str = Field(min_length=1, max_length=50)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    issue_date: date
    due_date: date
    notes: Optional[str] = Field(default=None, max_length=5000)
    line_items: list[InvoiceLineItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_due_date(self) -> "InvoiceCreate":
        if self.due_date < self.issue_date:
            raise ValueError("Due date cannot be before issue date")
        return self


class InvoiceUpdate(InvoiceNormalizers):
    model_config = ConfigDict(extra="forbid")

    customer_id: Optional[uuid.UUID] = None
    invoice_number: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=5000)
    line_items: Optional[list[InvoiceLineItemCreate]] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_due_date(self) -> "InvoiceUpdate":
        if (
            self.issue_date is not None
            and self.due_date is not None
            and self.due_date < self.issue_date
        ):
            raise ValueError("Due date cannot be before issue date")
        return self


class InvoiceStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InvoiceStatus


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    customer_id: uuid.UUID
    invoice_number: str
    status: InvoiceStatus
    currency: str
    issue_date: date
    due_date: date
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    notes: Optional[str]
    line_items: list[InvoiceLineItemResponse]
    created_at: datetime
    updated_at: datetime
