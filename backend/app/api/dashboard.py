import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.invoice import InvoiceStatus
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import (
    DashboardActivityLimitError,
    DashboardCurrencyError,
    DashboardPeriodError,
    get_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard_endpoint(
    currency: str = Query(
        default="GBP",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
    months: int = Query(default=12, ge=1, le=24),
    recent_activity_limit: int = Query(default=10, ge=1, le=50),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    customer_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    try:
        return get_dashboard(
            db,
            current_user.id,
            currency=currency,
            months=months,
            recent_activity_limit=recent_activity_limit,
            date_from=date_from,
            date_to=date_to,
            invoice_status=invoice_status,
            customer_id=customer_id,
        )
    except (
        DashboardActivityLimitError,
        DashboardCurrencyError,
        DashboardPeriodError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
