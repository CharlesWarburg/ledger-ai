import io
import os
import tempfile
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError, DecompressionBombWarning
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

MAX_IMAGE_PIXELS = 40_000_000
CONTENT_TYPE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class FileValidationError(ValueError):
    pass


class FileStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    content_type: str
    size_bytes: int
    content: bytes


def _safe_original_filename(filename: str) -> str:
    normalized = filename.strip()
    if not normalized:
        raise FileValidationError("Filename cannot be empty")
    if "/" in normalized or "\\" in normalized:
        raise FileValidationError("Filename must not contain path separators")
    if len(normalized) > 255:
        raise FileValidationError("Filename cannot exceed 255 characters")
    if any(ord(character) < 32 for character in normalized):
        raise FileValidationError("Filename contains invalid characters")
    return normalized


def _validate_pdf(content: bytes) -> str:
    if not content.startswith(b"%PDF-"):
        raise FileValidationError("File content is not a PDF")
    try:
        PdfReader(io.BytesIO(content), strict=True)
    except (PdfReadError, ValueError, OSError) as exc:
        raise FileValidationError("PDF file could not be parsed") from exc
    return "application/pdf"


def _validate_image(content: bytes) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise FileValidationError("Image dimensions are too large")
                formats = {"JPEG": "image/jpeg", "PNG": "image/png"}
                content_type = formats.get(image.format or "")
    except (
        DecompressionBombError,
        DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
    ) as exc:
        raise FileValidationError("Image file could not be parsed") from exc
    if content_type is None:
        raise FileValidationError("Only JPEG and PNG images are supported")
    return content_type


def validate_upload(
    filename: str,
    declared_content_type: Optional[str],
    content: bytes,
) -> ValidatedUpload:
    original_filename = _safe_original_filename(filename)
    size_bytes = len(content)
    if size_bytes == 0:
        raise FileValidationError("Uploaded file cannot be empty")
    if size_bytes > settings.max_upload_size_bytes:
        raise FileValidationError("Uploaded file exceeds the configured size limit")

    if content.startswith(b"%PDF-"):
        content_type = _validate_pdf(content)
    else:
        content_type = _validate_image(content)

    if declared_content_type and declared_content_type != content_type:
        raise FileValidationError(
            "Declared content type does not match the uploaded file"
        )
    return ValidatedUpload(
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        content=content,
    )


def _upload_directory(upload_directory: Optional[Path] = None) -> Path:
    directory = upload_directory or settings.upload_directory
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    return directory.resolve()


def _storage_path(
    storage_key: str,
    upload_directory: Optional[Path] = None,
) -> Path:
    root = _upload_directory(upload_directory)
    path = (root / storage_key).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise FileStorageError("Storage key is outside the upload directory") from exc
    return path


def store_upload(
    owner_id: uuid.UUID,
    upload: ValidatedUpload,
    upload_directory: Optional[Path] = None,
) -> str:
    extension = CONTENT_TYPE_EXTENSIONS[upload.content_type]
    storage_key = f"documents/{owner_id}/{uuid.uuid4()}{extension}"
    destination = _storage_path(storage_key, upload_directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(upload.content)
            temporary_name = temporary_file.name
        os.replace(temporary_name, destination)
    except OSError as exc:
        raise FileStorageError("Uploaded file could not be stored") from exc
    return storage_key


def delete_stored_upload(
    storage_key: str,
    upload_directory: Optional[Path] = None,
) -> None:
    path = _storage_path(storage_key, upload_directory)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise FileStorageError("Stored file could not be deleted") from exc
