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

from app.models.document_processing import DocumentProcessingStatus


class ExtractedInvoiceLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = Field(default=None, max_length=500)
    quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=3,
    )
    unit_price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=4,
    )
    vat_rate: Optional[Decimal] = Field(
        default=None,
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
            return value or None
        return value


class InvoiceExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: Optional[str] = Field(default=None, max_length=255)
    supplier_email: Optional[str] = Field(default=None, max_length=320)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    invoice_number: Optional[str] = Field(default=None, max_length=50)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    line_items: list[ExtractedInvoiceLineItem] = Field(
        default_factory=list,
        max_length=100,
    )
    subtotal: Optional[Decimal] = Field(default=None, ge=0)
    vat_total: Optional[Decimal] = Field(default=None, ge=0)
    total: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=5000)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator(
        "supplier_name",
        "customer_name",
        "invoice_number",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("supplier_email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_due_date(self) -> "InvoiceExtraction":
        if (
            self.issue_date is not None
            and self.due_date is not None
            and self.due_date < self.issue_date
        ):
            raise ValueError("Due date cannot be before issue date")
        return self


class DocumentProcessingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    document_id: uuid.UUID
    owner_id: uuid.UUID
    status: DocumentProcessingStatus
    provider: Optional[str]
    extracted_data: Optional[InvoiceExtraction]
    error_message: Optional[str]
    attempt_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DocumentProcessingReview(BaseModel):
    """Human-approved invoice data from an AI extraction."""

    model_config = ConfigDict(extra="forbid")

    extracted_data: InvoiceExtraction
