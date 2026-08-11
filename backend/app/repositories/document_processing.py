import uuid
from typing import Mapping, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_processing import DocumentProcessing


def add_document_processing_record(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    values: Optional[Mapping[str, object]] = None,
) -> DocumentProcessing:
    processing = DocumentProcessing(
        owner_id=owner_id,
        document_id=document_id,
        **dict(values or {}),
    )
    db.add(processing)
    return processing


def get_document_processing_record(
    db: Session,
    owner_id: uuid.UUID,
    processing_id: uuid.UUID,
) -> Optional[DocumentProcessing]:
    statement = select(DocumentProcessing).where(
        DocumentProcessing.id == processing_id,
        DocumentProcessing.owner_id == owner_id,
    )
    return db.scalar(statement)


def get_document_processing_for_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Optional[DocumentProcessing]:
    statement = select(DocumentProcessing).where(
        DocumentProcessing.document_id == document_id,
        DocumentProcessing.owner_id == owner_id,
    )
    return db.scalar(statement)


def update_document_processing_record(
    processing: DocumentProcessing,
    values: Mapping[str, object],
) -> DocumentProcessing:
    for field, value in values.items():
        setattr(processing, field, value)
    return processing
