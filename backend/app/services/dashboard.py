import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.invoice import InvoiceStatus
from app.repositories.dashboard import (
    get_balance_totals,
    get_invoice_status_metrics,
    get_monthly_cash_flow,
    get_revenue_total,
    list_recent_invoice_activity,
    list_recent_payment_activity,
)
from app.schemas.dashboard import (
    DashboardKpis,
    DashboardResponse,
    InvoiceStatusMetric,
    MonthlyCashFlowPoint,
    RecentActivityItem,
    RecentActivityType,
)

MIN_DASHBOARD_MONTHS = 1
MAX_DASHBOARD_MONTHS = 24
MIN_RECENT_ACTIVITY_LIMIT = 1
MAX_RECENT_ACTIVITY_LIMIT = 50


class DashboardPeriodError(ValueError):
    pass


class DashboardCurrencyError(ValueError):
    pass


class DashboardActivityLimitError(ValueError):
    pass


def _normalize_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise DashboardCurrencyError("Currency must be a three-letter code")
    return normalized


def _shift_month(month: date, offset: int) -> date:
    month_index = month.year * 12 + month.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return date(year, zero_based_month + 1, 1)


def _reporting_period(months: int, as_of_date: date) -> tuple[date, date]:
    if not MIN_DASHBOARD_MONTHS <= months <= MAX_DASHBOARD_MONTHS:
        raise DashboardPeriodError(
            f"Dashboard period must be between {MIN_DASHBOARD_MONTHS} "
            f"and {MAX_DASHBOARD_MONTHS} months"
        )
    current_month = as_of_date.replace(day=1)
    return _shift_month(current_month, -(months - 1)), as_of_date


def _resolve_reporting_period(
    months: int,
    as_of_date: date,
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[date, date]:
    if (date_from is None) != (date_to is None):
        raise DashboardPeriodError(
            "Dashboard date_from and date_to must be supplied together"
        )
    if date_from is None or date_to is None:
        return _reporting_period(months, as_of_date)
    if date_to < date_from:
        raise DashboardPeriodError(
            "Dashboard period end cannot be before its start"
        )
    month_span = (
        (date_to.year - date_from.year) * 12
        + date_to.month
        - date_from.month
        + 1
    )
    if month_span > MAX_DASHBOARD_MONTHS:
        raise DashboardPeriodError(
            f"Dashboard date range cannot exceed {MAX_DASHBOARD_MONTHS} months"
        )
    return date_from, date_to


def _complete_status_metrics(
    raw_metrics: list[tuple[InvoiceStatus, int, Decimal]],
) -> list[InvoiceStatusMetric]:
    metrics_by_status = {
        status: (count, total_amount)
        for status, count, total_amount in raw_metrics
    }
    return [
        InvoiceStatusMetric(
            status=status,
            count=metrics_by_status.get(status, (0, 0))[0],
            total_amount=metrics_by_status.get(status, (0, 0))[1],
        )
        for status in InvoiceStatus
    ]


def _complete_cash_flow(
    period_start: date,
    period_end: date,
    raw_cash_flow: list[tuple[date, Decimal]],
) -> list[MonthlyCashFlowPoint]:
    amounts_by_month = dict(raw_cash_flow)
    points: list[MonthlyCashFlowPoint] = []
    month = period_start.replace(day=1)
    final_month = period_end.replace(day=1)
    while month <= final_month:
        points.append(
            MonthlyCashFlowPoint(
                month=month,
                amount=amounts_by_month.get(month, 0),
            )
        )
        month = _shift_month(month, 1)
    return points


def get_dashboard(
    db: Session,
    owner_id: uuid.UUID,
    currency: str = "GBP",
    months: int = 12,
    recent_activity_limit: int = 10,
    as_of_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
) -> DashboardResponse:
    if not MIN_RECENT_ACTIVITY_LIMIT <= recent_activity_limit <= MAX_RECENT_ACTIVITY_LIMIT:
        raise DashboardActivityLimitError(
            f"Recent activity limit must be between "
            f"{MIN_RECENT_ACTIVITY_LIMIT} and {MAX_RECENT_ACTIVITY_LIMIT}"
        )

    normalized_currency = _normalize_currency(currency)
    effective_date = as_of_date or date.today()
    period_start, period_end = _resolve_reporting_period(
        months,
        effective_date,
        date_from,
        date_to,
    )

    total_revenue = get_revenue_total(
        db,
        owner_id,
        normalized_currency,
        period_start,
        period_end,
        invoice_status=invoice_status,
        customer_id=customer_id,
    )
    outstanding_amount, overdue_amount = get_balance_totals(
        db,
        owner_id,
        normalized_currency,
        period_end,
        invoice_status=invoice_status,
        customer_id=customer_id,
    )
    status_metrics = _complete_status_metrics(
        get_invoice_status_metrics(
            db,
            owner_id,
            normalized_currency,
            period_start,
            period_end,
            invoice_status=invoice_status,
            customer_id=customer_id,
        )
    )
    monthly_cash_flow = _complete_cash_flow(
        period_start,
        period_end,
        get_monthly_cash_flow(
            db,
            owner_id,
            normalized_currency,
            period_start,
            period_end,
            invoice_status=invoice_status,
            customer_id=customer_id,
        ),
    )

    invoices = list_recent_invoice_activity(
        db,
        owner_id,
        normalized_currency,
        period_start,
        period_end,
        limit=recent_activity_limit,
        invoice_status=invoice_status,
        customer_id=customer_id,
    )
    payments = list_recent_payment_activity(
        db,
        owner_id,
        normalized_currency,
        period_start,
        period_end,
        limit=recent_activity_limit,
        invoice_status=invoice_status,
        customer_id=customer_id,
    )
    recent_activity = [
        RecentActivityItem(
            activity_type=RecentActivityType.INVOICE_CREATED,
            entity_id=invoice.id,
            invoice_id=invoice.id,
            description=f"Invoice {invoice.invoice_number} created",
            amount=invoice.total,
            occurred_at=invoice.created_at,
        )
        for invoice in invoices
    ]
    recent_activity.extend(
        RecentActivityItem(
            activity_type=RecentActivityType.PAYMENT_RECEIVED,
            entity_id=payment.id,
            invoice_id=payment.invoice_id,
            description="Payment received",
            amount=payment.amount,
            occurred_at=payment.created_at,
        )
        for payment in payments
    )
    recent_activity.sort(key=lambda activity: activity.occurred_at, reverse=True)
    recent_activity = recent_activity[:recent_activity_limit]

    paid_invoice_count = next(
        metric.count
        for metric in status_metrics
        if metric.status == InvoiceStatus.PAID
    )
    return DashboardResponse(
        currency=normalized_currency,
        period_start=period_start,
        period_end=period_end,
        kpis=DashboardKpis(
            total_revenue=total_revenue,
            outstanding_amount=outstanding_amount,
            overdue_amount=overdue_amount,
            paid_invoice_count=paid_invoice_count,
        ),
        invoice_statuses=status_metrics,
        monthly_cash_flow=monthly_cash_flow,
        recent_activity=recent_activity,
    )
