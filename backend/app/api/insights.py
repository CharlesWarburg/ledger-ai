from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.insights import DuplicateInvoiceInsightsResponse
from app.services.insights import (
    InsightCurrencyError,
    InsightDateRangeError,
    list_duplicate_invoices,
)

router = APIRouter(prefix="/insights", tags=["insights"])


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
