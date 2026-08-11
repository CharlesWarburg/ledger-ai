import uuid
import json
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.insights import (
    list_duplicate_invoice_candidates,
    list_overdue_invoice_balances,
    list_outstanding_invoice_balances,
)
from app.schemas.insights import (
    CashFlowForecastPoint,
    CashFlowForecastResponse,
    DuplicateInvoiceInsightsResponse,
    DuplicateInvoiceMatch,
    SlowPayerInsight,
    SlowPayerInsightsResponse,
    ExecutiveSummaryResponse,
)
from app.services.ai_provider import OpenAIInvoiceExtractionProvider


class InsightCurrencyError(ValueError):
    pass


class InsightDateRangeError(ValueError):
    pass


class InsightForecastPeriodError(ValueError):
    pass


def _shift_month(month: date, offset: int) -> date:
    month_index = month.year * 12 + month.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    return date(year, zero_based_month + 1, 1)


def get_cash_flow_forecast(
    db: Session,
    owner_id: uuid.UUID,
    currency: str = "GBP",
    months: int = 6,
    as_of_date: Optional[date] = None,
) -> CashFlowForecastResponse:
    if not 1 <= months <= 24:
        raise InsightForecastPeriodError(
            "Forecast period must be between 1 and 24 months"
        )
    normalized_currency = currency.strip().upper()
    if len(normalized_currency) != 3 or not normalized_currency.isalpha():
        raise InsightCurrencyError("Currency must be a three-letter code")

    effective_date = as_of_date or date.today()
    first_month = effective_date.replace(day=1)
    forecast_months = [_shift_month(first_month, index) for index in range(months)]
    final_month = forecast_months[-1]
    final_day = _shift_month(final_month, 1) - date.resolution
    amounts = {month: {"expected": 0, "overdue": 0, "count": 0} for month in forecast_months}

    for due_date, balance in list_outstanding_invoice_balances(
        db,
        owner_id,
        normalized_currency,
        effective_date,
        final_day,
    ):
        if due_date < effective_date:
            bucket = first_month
            amounts[bucket]["overdue"] += balance
        else:
            bucket = due_date.replace(day=1)
            amounts[bucket]["expected"] += balance
        amounts[bucket]["count"] += 1

    return CashFlowForecastResponse(
        currency=normalized_currency,
        as_of_date=effective_date,
        months=[
            CashFlowForecastPoint(
                month=month,
                expected_receipts=values["expected"],
                overdue_receipts=values["overdue"],
                invoice_count=values["count"],
            )
            for month, values in amounts.items()
        ],
    )


def list_slow_payers(
    db: Session,
    owner_id: uuid.UUID,
    currency: str = "GBP",
    as_of_date: Optional[date] = None,
    limit: int = 50,
) -> SlowPayerInsightsResponse:
    normalized_currency = currency.strip().upper()
    if len(normalized_currency) != 3 or not normalized_currency.isalpha():
        raise InsightCurrencyError("Currency must be a three-letter code")
    effective_date = as_of_date or date.today()
    grouped: dict[uuid.UUID, dict[str, object]] = {}
    for customer, due_date, balance in list_overdue_invoice_balances(
        db,
        owner_id,
        normalized_currency,
        effective_date,
    ):
        current = grouped.setdefault(
            customer.id,
            {
                "customer_name": customer.name,
                "overdue_invoice_count": 0,
                "overdue_balance": 0,
                "longest_days_overdue": 0,
            },
        )
        current["overdue_invoice_count"] = int(
            current["overdue_invoice_count"]
        ) + 1
        current["overdue_balance"] = current["overdue_balance"] + balance
        current["longest_days_overdue"] = max(
            int(current["longest_days_overdue"]),
            (effective_date - due_date).days,
        )

    customers = [
        SlowPayerInsight(customer_id=customer_id, **values)
        for customer_id, values in grouped.items()
    ]
    customers.sort(
        key=lambda customer: (
            customer.overdue_balance,
            customer.longest_days_overdue,
        ),
        reverse=True,
    )
    return SlowPayerInsightsResponse(
        currency=normalized_currency,
        as_of_date=effective_date,
        customers=customers[:limit],
    )


def generate_executive_summary(
    db: Session,
    owner_id: uuid.UUID,
    provider: OpenAIInvoiceExtractionProvider,
    currency: str = "GBP",
    as_of_date: Optional[date] = None,
) -> ExecutiveSummaryResponse:
    effective_date = as_of_date or date.today()
    snapshot = {
        "duplicates": list_duplicate_invoices(
            db, owner_id, currency=currency
        ).model_dump(mode="json"),
        "cash_flow_forecast": get_cash_flow_forecast(
            db, owner_id, currency=currency, as_of_date=effective_date
        ).model_dump(mode="json"),
        "slow_payers": list_slow_payers(
            db, owner_id, currency=currency, as_of_date=effective_date
        ).model_dump(mode="json"),
    }
    return provider.generate_executive_summary(json.dumps(snapshot))


def list_duplicate_invoices(
    db: Session,
    owner_id: uuid.UUID,
    currency: Optional[str] = None,
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    limit: int = 100,
) -> DuplicateInvoiceInsightsResponse:
    if issue_date_from is not None and issue_date_to is not None:
        if issue_date_to < issue_date_from:
            raise InsightDateRangeError(
                "Invoice issue-date end cannot be before its start"
            )
    normalized_currency = None
    if currency is not None:
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise InsightCurrencyError("Currency must be a three-letter code")

    candidates = list_duplicate_invoice_candidates(
        db,
        owner_id,
        currency=normalized_currency,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        limit=limit,
    )
    return DuplicateInvoiceInsightsResponse(
        matches=[
            DuplicateInvoiceMatch(
                first_invoice_id=first_invoice.id,
                first_invoice_number=first_invoice.invoice_number,
                second_invoice_id=second_invoice.id,
                second_invoice_number=second_invoice.invoice_number,
                customer_id=customer.id,
                customer_name=customer.name,
                currency=first_invoice.currency,
                total=first_invoice.total,
                issue_date=first_invoice.issue_date,
            )
            for first_invoice, second_invoice, customer in candidates
        ]
    )
