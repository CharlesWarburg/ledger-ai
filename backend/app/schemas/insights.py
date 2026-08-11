import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DuplicateInvoiceMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_invoice_id: uuid.UUID
    first_invoice_number: str = Field(min_length=1, max_length=50)
    second_invoice_id: uuid.UUID
    second_invoice_number: str = Field(min_length=1, max_length=50)
    customer_id: uuid.UUID
    customer_name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3)
    total: Decimal = Field(ge=0)
    issue_date: date

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class DuplicateInvoiceInsightsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matches: list[DuplicateInvoiceMatch]


class CashFlowForecastPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: date
    expected_receipts: Decimal = Field(ge=0)
    overdue_receipts: Decimal = Field(ge=0)
    invoice_count: int = Field(ge=0)


class CashFlowForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    as_of_date: date
    months: list[CashFlowForecastPoint]

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value
