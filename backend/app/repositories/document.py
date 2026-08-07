import uuid
from typing import Mapping, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType


def add_document_record(
    db: Session,
    owner_id: uuid.UUID,
    values: Mapping[str, object],
) -> Document:
    document = Document(owner_id=owner_id, **dict(values))
    db.add(document)
    return document


def list_document_records(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: Optional[uuid.UUID] = None,
    document_type: Optional[DocumentType] = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Document]:
    statement = select(Document).where(Document.owner_id == owner_id)
    if invoice_id is not None:
        statement = statement.where(Document.invoice_id == invoice_id)
    if document_type is not None:
        statement = statement.where(Document.document_type == document_type)
    statement = (
        statement.order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_document_record(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Optional[Document]:
    statement = select(Document).where(
        Document.id == document_id,
        Document.owner_id == owner_id,
    )
    return db.scalar(statement)


def update_document_record(
    document: Document,
    values: Mapping[str, object],
) -> Document:
    for field, value in values.items():
        setattr(document, field, value)
    return document


def delete_document_record(db: Session, document: Document) -> None:
    db.delete(document)
