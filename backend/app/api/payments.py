import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentUpdate
from app.services.payment import (
    PaymentDateError,
    PaymentExceedsOutstandingBalanceError,
    PaymentInvoiceNotFoundError,
    PaymentInvoiceStatusError,
    PaymentNotFoundError,
    create_payment,
    delete_payment,
    get_payment,
    list_payments,
    update_payment,
)

router = APIRouter(tags=["payments"])


def _payment_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Payment not found",
    )


def _invoice_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invoice not found",
    )


def _payment_conflict(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    )


def _invalid_payment_date(exc: PaymentDateError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_endpoint(
    invoice_id: uuid.UUID,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = create_payment(
            db,
            current_user.id,
            invoice_id,
            payment_data,
        )
    except PaymentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    except (
        PaymentExceedsOutstandingBalanceError,
        PaymentInvoiceStatusError,
    ) as exc:
        raise _payment_conflict(exc) from exc
    except PaymentDateError as exc:
        raise _invalid_payment_date(exc) from exc
    return PaymentResponse.model_validate(payment)


@router.get(
    "/invoices/{invoice_id}/payments",
    response_model=list[PaymentResponse],
)
def list_payments_endpoint(
    invoice_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    try:
        payments = list_payments(
            db,
            current_user.id,
            invoice_id,
            offset=offset,
            limit=limit,
        )
    except PaymentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    return [PaymentResponse.model_validate(payment) for payment in payments]


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_endpoint(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = get_payment(db, current_user.id, payment_id)
    except PaymentNotFoundError as exc:
        raise _payment_not_found() from exc
    return PaymentResponse.model_validate(payment)


@router.patch("/payments/{payment_id}", response_model=PaymentResponse)
def update_payment_endpoint(
    payment_id: uuid.UUID,
    payment_data: PaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment = update_payment(
            db,
            current_user.id,
            payment_id,
            payment_data,
        )
    except PaymentNotFoundError as exc:
        raise _payment_not_found() from exc
    except PaymentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    except PaymentExceedsOutstandingBalanceError as exc:
        raise _payment_conflict(exc) from exc
    except PaymentDateError as exc:
        raise _invalid_payment_date(exc) from exc
    return PaymentResponse.model_validate(payment)


@router.delete(
    "/payments/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_payment_endpoint(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        delete_payment(db, current_user.id, payment_id)
    except PaymentNotFoundError as exc:
        raise _payment_not_found() from exc
    except PaymentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
