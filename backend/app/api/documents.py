import logging
import uuid
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.document import DocumentType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.schemas.document_processing import (
    DocumentProcessingInvoiceCreate,
    DocumentProcessingResponse,
    DocumentProcessingReview,
)
from app.schemas.invoice import InvoiceResponse
from app.services.document import (
    DocumentInvoiceNotFoundError,
    DocumentNotFoundError,
    create_document,
    delete_document,
    get_document,
    get_document_content,
    list_documents,
    update_document,
)
from app.services.storage import FileStorageError, FileValidationError
from app.services.document_processing import (
    DocumentProcessingExecutionError,
    DocumentProcessingInvoiceAlreadyCreatedError,
    DocumentProcessingInvoiceDataError,
    DocumentProcessingInvalidStateError,
    DocumentProcessingInProgressError,
    DocumentProcessingNotFoundError,
    create_invoice_from_document_processing,
    get_document_processing_for_source_document,
    process_document,
    review_document_processing,
)
from app.services.invoice import (
    InvoiceCustomerNotFoundError,
    InvoiceNumberAlreadyExistsError,
)
from app.services.ai_provider import (
    AIProviderNotConfiguredError,
    OpenAIInvoiceExtractionProvider,
)

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


def _document_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found",
    )


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


def _file_validation_error(exc: FileValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


def _storage_error(exc: FileStorageError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Document storage operation failed",
    )


def _processing_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document processing record not found",
    )


def _processing_invalid_state(exc: DocumentProcessingInvalidStateError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    )


def _processing_execution_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Document processing provider failed",
    )


def _processing_not_configured() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Document processing provider is not configured",
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_endpoint(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(default=DocumentType.OTHER),
    invoice_id: Optional[uuid.UUID] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        document = create_document(
            db,
            current_user.id,
            DocumentCreate(document_type=document_type, invoice_id=invoice_id),
            file.filename or "",
            file.content_type,
            await file.read(),
        )
    except DocumentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    except FileValidationError as exc:
        raise _file_validation_error(exc) from exc
    except FileStorageError as exc:
        logger.exception(
            "Document upload storage failed | owner_id=%s error_type=%s",
            current_user.id,
            type(exc).__name__,
        )
        raise _storage_error(exc) from exc
    finally:
        await file.close()
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents_endpoint(
    invoice_id: Optional[uuid.UUID] = None,
    document_type: Optional[DocumentType] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    try:
        documents = list_documents(
            db,
            current_user.id,
            invoice_id=invoice_id,
            document_type=document_type,
            offset=offset,
            limit=limit,
        )
    except DocumentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        document = get_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
def download_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        document, content = get_document_content(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except FileStorageError as exc:
        logger.exception(
            "Document download storage failed | document_id=%s owner_id=%s error_type=%s",
            document_id,
            current_user.id,
            type(exc).__name__,
        )
        raise _storage_error(exc) from exc
    filename = quote(document.original_filename)
    return Response(
        content=content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        },
    )


@router.get("/{document_id}/processing", response_model=DocumentProcessingResponse)
def get_document_processing_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentProcessingResponse:
    try:
        processing = get_document_processing_for_source_document(
            db,
            current_user.id,
            document_id,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except DocumentProcessingNotFoundError as exc:
        raise _processing_not_found() from exc
    return DocumentProcessingResponse.model_validate(processing)


@router.post("/{document_id}/processing", response_model=DocumentProcessingResponse)
def process_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentProcessingResponse:
    try:
        provider = OpenAIInvoiceExtractionProvider(
            settings.openai_api_key.get_secret_value(),
            settings.openai_invoice_model,
        )
        processing = process_document(
            db,
            current_user.id,
            document_id,
            provider,
        )
    except AIProviderNotConfiguredError as exc:
        raise _processing_not_configured() from exc
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except DocumentProcessingInProgressError as exc:
        raise _processing_invalid_state(exc) from exc
    except DocumentProcessingInvalidStateError as exc:
        raise _processing_invalid_state(exc) from exc
    except DocumentProcessingExecutionError as exc:
        raise _processing_execution_error() from exc
    return DocumentProcessingResponse.model_validate(processing)


@router.patch(
    "/{document_id}/processing/review",
    response_model=DocumentProcessingResponse,
)
def review_document_processing_endpoint(
    document_id: uuid.UUID,
    review_data: DocumentProcessingReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentProcessingResponse:
    try:
        processing = review_document_processing(
            db,
            current_user.id,
            document_id,
            review_data.extracted_data,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except DocumentProcessingNotFoundError as exc:
        raise _processing_not_found() from exc
    except DocumentProcessingInvalidStateError as exc:
        raise _processing_invalid_state(exc) from exc
    return DocumentProcessingResponse.model_validate(processing)


@router.post(
    "/{document_id}/processing/create-invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_from_document_processing_endpoint(
    document_id: uuid.UUID,
    invoice_data: DocumentProcessingInvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    try:
        invoice = create_invoice_from_document_processing(
            db,
            current_user.id,
            document_id,
            invoice_data.customer_id,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except DocumentProcessingNotFoundError as exc:
        raise _processing_not_found() from exc
    except DocumentProcessingInvoiceDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except (
        DocumentProcessingInvalidStateError,
        DocumentProcessingInvoiceAlreadyCreatedError,
    ) as exc:
        raise _processing_invalid_state(exc) from exc
    except InvoiceCustomerNotFoundError as exc:
        raise _customer_not_found() from exc
    except InvoiceNumberAlreadyExistsError as exc:
        raise _duplicate_invoice_number() from exc
    return InvoiceResponse.model_validate(invoice)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document_endpoint(
    document_id: uuid.UUID,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        document = update_document(
            db,
            current_user.id,
            document_id,
            document_data,
        )
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except DocumentInvoiceNotFoundError as exc:
        raise _invoice_not_found() from exc
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        delete_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise _document_not_found() from exc
    except FileStorageError as exc:
        logger.exception(
            "Document deletion storage failed | document_id=%s owner_id=%s error_type=%s",
            document_id,
            current_user.id,
            type(exc).__name__,
        )
        raise _storage_error(exc) from exc
