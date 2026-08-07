import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: DocumentType = DocumentType.OTHER
    invoice_id: Optional[uuid.UUID] = None


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Optional[DocumentType] = None
    invoice_id: Optional[uuid.UUID] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    owner_id: uuid.UUID
    invoice_id: Optional[uuid.UUID]
    document_type: DocumentType
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
