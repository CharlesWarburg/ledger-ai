from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.insights import (
    CashFlowForecastResponse,
    DuplicateInvoiceInsightsResponse,
    SlowPayerInsightsResponse,
    ExecutiveSummaryResponse,
)
from app.services.ai_provider import (
    AIProviderNotConfiguredError,
    AIProviderProcessingError,
    OpenAIInvoiceExtractionProvider,
)
from app.services.insights import (
    InsightCurrencyError,
    InsightDateRangeError,
    InsightForecastPeriodError,
    get_cash_flow_forecast,
    generate_executive_summary,
    list_duplicate_invoices,
    list_slow_payers,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/executive-summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary_endpoint(
    currency: str = Query(default="GBP", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
    as_of_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveSummaryResponse:
    try:
        provider = OpenAIInvoiceExtractionProvider(
            settings.openai_api_key.get_secret_value(),
            settings.openai_invoice_model,
        )
        return generate_executive_summary(
            db, current_user.id, provider, currency=currency, as_of_date=as_of_date
        )
    except AIProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Executive summary provider is not configured") from exc
    except AIProviderProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Executive summary provider failed") from exc
    except InsightCurrencyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/slow-payers", response_model=SlowPayerInsightsResponse)
def list_slow_payers_endpoint(
    currency: str = Query(
        default="GBP",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
    as_of_date: Optional[date] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SlowPayerInsightsResponse:
    try:
        return list_slow_payers(
            db,
            current_user.id,
            currency=currency,
            as_of_date=as_of_date,
            limit=limit,
        )
    except InsightCurrencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/cash-flow-forecast", response_model=CashFlowForecastResponse)
def get_cash_flow_forecast_endpoint(
    currency: str = Query(
        default="GBP",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
    months: int = Query(default=6, ge=1, le=24),
    as_of_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CashFlowForecastResponse:
    try:
        return get_cash_flow_forecast(
            db,
            current_user.id,
            currency=currency,
            months=months,
            as_of_date=as_of_date,
        )
    except (InsightCurrencyError, InsightForecastPeriodError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get("/duplicates", response_model=DuplicateInvoiceInsightsResponse)
def list_duplicate_invoices_endpoint(
    currency: Optional[str] = Query(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
    issue_date_from: Optional[date] = None,
    issue_date_to: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DuplicateInvoiceInsightsResponse:
    try:
        return list_duplicate_invoices(
            db,
            current_user.id,
            currency=currency,
            issue_date_from=issue_date_from,
            issue_date_to=issue_date_to,
            limit=limit,
        )
    except (InsightCurrencyError, InsightDateRangeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
