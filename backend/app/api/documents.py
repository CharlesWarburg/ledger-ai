import uuid
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.document import DocumentType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
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

router = APIRouter(prefix="/documents", tags=["documents"])


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
        raise _storage_error(exc) from exc
    filename = quote(document.original_filename)
    return Response(
        content=content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        },
    )


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
        raise _storage_error(exc) from exc
