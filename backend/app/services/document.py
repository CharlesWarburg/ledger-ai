import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType
from app.repositories.document import (
    add_document_record,
    delete_document_record,
    get_document_record,
    list_document_records,
    update_document_record,
)
from app.repositories.invoice import get_invoice_record
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.storage import (
    delete_stored_upload,
    read_stored_upload,
    store_upload,
    validate_upload,
)


class DocumentNotFoundError(ValueError):
    pass


class DocumentInvoiceNotFoundError(ValueError):
    pass


def _require_owned_invoice(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> None:
    if get_invoice_record(db, owner_id, invoice_id) is None:
        raise DocumentInvoiceNotFoundError("Invoice not found")


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def create_document(
    db: Session,
    owner_id: uuid.UUID,
    document_data: DocumentCreate,
    filename: str,
    declared_content_type: Optional[str],
    content: bytes,
    upload_directory: Optional[Path] = None,
) -> Document:
    if document_data.invoice_id is not None:
        _require_owned_invoice(db, owner_id, document_data.invoice_id)

    upload = validate_upload(filename, declared_content_type, content)
    storage_key = store_upload(owner_id, upload, upload_directory)
    values = document_data.model_dump()
    values.update(
        {
            "original_filename": upload.original_filename,
            "storage_key": storage_key,
            "content_type": upload.content_type,
            "size_bytes": upload.size_bytes,
        }
    )
    document = add_document_record(db, owner_id, values)
    try:
        _commit(db)
        db.refresh(document)
    except Exception:
        delete_stored_upload(storage_key, upload_directory)
        raise
    return document


def list_documents(
    db: Session,
    owner_id: uuid.UUID,
    invoice_id: Optional[uuid.UUID] = None,
    document_type: Optional[DocumentType] = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Document]:
    if invoice_id is not None:
        _require_owned_invoice(db, owner_id, invoice_id)
    return list_document_records(
        db,
        owner_id,
        invoice_id=invoice_id,
        document_type=document_type,
        offset=offset,
        limit=limit,
    )


def get_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    document = get_document_record(db, owner_id, document_id)
    if document is None:
        raise DocumentNotFoundError("Document not found")
    return document


def get_document_content(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    upload_directory: Optional[Path] = None,
) -> tuple[Document, bytes]:
    document = get_document(db, owner_id, document_id)
    return document, read_stored_upload(document.storage_key, upload_directory)


def update_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    document_data: DocumentUpdate,
) -> Document:
    document = get_document(db, owner_id, document_id)
    values = document_data.model_dump(exclude_unset=True)
    invoice_id = values.get("invoice_id")
    if invoice_id is not None:
        _require_owned_invoice(db, owner_id, invoice_id)
    update_document_record(document, values)
    _commit(db)
    db.refresh(document)
    return document


def delete_document(
    db: Session,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    upload_directory: Optional[Path] = None,
) -> None:
    document = get_document(db, owner_id, document_id)
    storage_key = document.storage_key
    delete_document_record(db, document)
    _commit(db)
    delete_stored_upload(storage_key, upload_directory)
