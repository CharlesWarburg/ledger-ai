import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document_processing import (
    DocumentProcessing,
    DocumentProcessingStatus,
)
from app.repositories.document_processing import (
    add_document_processing_record,
    get_document_processing_for_document,
    get_document_processing_record,
    update_document_processing_record,
)
from app.services.ai_provider import InvoiceExtractionProvider
from app.services.document import get_document
from app.services.storage import read_stored_upload
from app.schemas.document_processing import InvoiceExtraction


class DocumentProcessingNotFoundError(ValueError):
    pass


class DocumentProcessingInProgressError(ValueError):
    pass


class DocumentProcessingInvalidStateError(ValueError):
    pass


class DocumentProcessingExecutionError(RuntimeError):
    pass


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_document_processing(
    db: Session,
    owner_id: uuid.UUID,
    processing_id: uuid.UUID,
) -> DocumentProcessing:
    processing = get_document_processing_record(db, owner_id, processing_id)
    if processing is None:
        raise DocumentProcessingNotFoundError("Document processing record not found")
    return processing


def get_document_processing_for_source_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    get_document(db, owner_id, document_id)
    processing = get_document_processing_for_document(db, owner_id, document_id)
    if processing is None:
        raise DocumentProcessingNotFoundError("Document processing record not found")
    return processing


def _mark_processing_failed(
    db: Session,
    processing: DocumentProcessing,
    error: Exception,
) -> None:
    update_document_processing_record(
        processing,
        {
            "status": DocumentProcessingStatus.FAILED,
            "error_message": str(error),
            "completed_at": _now(),
        },
    )
    _commit(db)


def process_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    provider: InvoiceExtractionProvider,
    upload_directory: Optional[Path] = None,
) -> DocumentProcessing:
    document = get_document(db, owner_id, document_id)
    processing = get_document_processing_for_document(db, owner_id, document_id)
    if processing is None:
        processing = add_document_processing_record(
            db,
            owner_id,
            document_id,
            values={"attempt_count": 0},
        )
    elif processing.status == DocumentProcessingStatus.PROCESSING:
        raise DocumentProcessingInProgressError(
            "Document processing is already in progress"
        )
    elif processing.status in {
        DocumentProcessingStatus.REVIEW_REQUIRED,
        DocumentProcessingStatus.COMPLETED,
    }:
        raise DocumentProcessingInvalidStateError(
            "Document processing must be reviewed before it can be run again"
        )

    update_document_processing_record(
        processing,
        {
            "status": DocumentProcessingStatus.PROCESSING,
            "provider": provider.name,
            "error_message": None,
            "started_at": _now(),
            "completed_at": None,
            "attempt_count": processing.attempt_count + 1,
        },
    )
    _commit(db)

    try:
        content = read_stored_upload(document.storage_key, upload_directory)
        extraction = provider.extract_invoice(content, document.content_type)
    except Exception as exc:
        _mark_processing_failed(db, processing, exc)
        raise DocumentProcessingExecutionError(
            "Document processing failed"
        ) from exc

    update_document_processing_record(
        processing,
        {
            "status": DocumentProcessingStatus.REVIEW_REQUIRED,
            "extracted_data": extraction.model_dump(mode="json"),
            "completed_at": _now(),
        },
    )
    _commit(db)
    db.refresh(processing)
    return processing


def review_document_processing(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    extracted_data: InvoiceExtraction,
) -> DocumentProcessing:
    """Save human-approved data without yet creating an invoice automatically."""
    processing = get_document_processing_for_source_document(
        db,
        owner_id,
        document_id,
    )
    if processing.status != DocumentProcessingStatus.REVIEW_REQUIRED:
        raise DocumentProcessingInvalidStateError(
            "Only processing records awaiting review can be approved"
        )

    update_document_processing_record(
        processing,
        {
            "status": DocumentProcessingStatus.COMPLETED,
            "extracted_data": extracted_data.model_dump(mode="json"),
            "error_message": None,
            "completed_at": _now(),
        },
    )
    _commit(db)
    db.refresh(processing)
    return processing
