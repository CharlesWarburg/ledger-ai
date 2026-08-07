import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.invoice import InvoiceStatus


class DashboardKpis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_revenue: Decimal = Field(ge=0)
    outstanding_amount: Decimal = Field(ge=0)
    overdue_amount: Decimal = Field(ge=0)
    paid_invoice_count: int = Field(ge=0)


class InvoiceStatusMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InvoiceStatus
    count: int = Field(ge=0)
    total_amount: Decimal = Field(ge=0)


class MonthlyCashFlowPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: date
    amount: Decimal = Field(ge=0)

    @field_validator("month")
    @classmethod
    def require_first_day_of_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Cash-flow month must be the first day of a month")
        return value


class RecentActivityType(str, enum.Enum):
    INVOICE_CREATED = "invoice_created"
    PAYMENT_RECEIVED = "payment_received"


class RecentActivityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_type: RecentActivityType
    entity_id: uuid.UUID
    invoice_id: uuid.UUID
    description: str = Field(min_length=1, max_length=500)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    occurred_at: datetime


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3)
    period_start: date
    period_end: date
    kpis: DashboardKpis
    invoice_statuses: list[InvoiceStatusMetric]
    monthly_cash_flow: list[MonthlyCashFlowPoint]
    recent_activity: list[RecentActivityItem]

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_period(self) -> "DashboardResponse":
        if self.period_end < self.period_start:
            raise ValueError("Dashboard period end cannot be before its start")
        return self
