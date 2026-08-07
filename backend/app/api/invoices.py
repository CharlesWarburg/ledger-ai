import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceStatusUpdate,
    InvoiceUpdate,
)
from app.services.invoice import (
    InvalidInvoiceStatusTransitionError,
    InvoiceCustomerNotFoundError,
    InvoiceDateError,
    InvoiceNotFoundError,
    InvoiceNumberAlreadyExistsError,
    create_invoice,
    delete_invoice,
    get_invoice,
    list_invoices,
    update_invoice,
    update_invoice_status,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _invoice_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invoice not found",
    )


def _customer_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Customer not found",
    )


def _duplicate_invoice_number() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Invoice number is already in use",
    )


def _invalid_invoice_dates(exc: InvoiceDateError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


def _invalid_status_transition(
    exc: InvalidInvoiceStatusTransitionError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    )


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_endpoint(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    try:
        invoice = create_invoice(db, current_user.id, invoice_data)
    except InvoiceCustomerNotFoundError as exc:
        raise _customer_not_found() from exc
    except InvoiceNumberAlreadyExistsError as exc:
        raise _duplicate_invoice_number() from exc
    return InvoiceResponse.model_validate(invoice)


@router.get("", response_model=list[InvoiceResponse])
def list_invoices_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoiceResponse]:
    invoices = list_invoices(
        db,
        current_user.id,
        offset=offset,
        limit=limit,
    )
    return [InvoiceResponse.model_validate(invoice) for invoice in invoices]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    try:
        invoice = get_invoice(db, current_user.id, invoice_id)
    except InvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    return InvoiceResponse.model_validate(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice_endpoint(
    invoice_id: uuid.UUID,
    invoice_data: InvoiceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    try:
        invoice = update_invoice(
            db,
            current_user.id,
            invoice_id,
            invoice_data,
        )
    except InvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    except InvoiceCustomerNotFoundError as exc:
        raise _customer_not_found() from exc
    except InvoiceNumberAlreadyExistsError as exc:
        raise _duplicate_invoice_number() from exc
    except InvoiceDateError as exc:
        raise _invalid_invoice_dates(exc) from exc
    return InvoiceResponse.model_validate(invoice)


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status_endpoint(
    invoice_id: uuid.UUID,
    status_data: InvoiceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    try:
        invoice = update_invoice_status(
            db,
            current_user.id,
            invoice_id,
            status_data.status,
        )
    except InvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    except InvalidInvoiceStatusTransitionError as exc:
        raise _invalid_status_transition(exc) from exc
    return InvoiceResponse.model_validate(invoice)


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        delete_invoice(db, current_user.id, invoice_id)
    except InvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
