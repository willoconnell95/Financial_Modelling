import os
import uuid
import mimetypes
from pathlib import Path
from app.models.document import DocumentType


MIME_TO_DOCTYPE = {
    "application/pdf": DocumentType.PDF,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.EXCEL,
    "application/vnd.ms-excel": DocumentType.EXCEL,
    "text/csv": DocumentType.CSV,
    "application/csv": DocumentType.CSV,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
    "application/msword": DocumentType.DOCX,
    "image/png": DocumentType.IMAGE,
    "image/jpeg": DocumentType.IMAGE,
    "image/jpg": DocumentType.IMAGE,
    "image/tiff": DocumentType.IMAGE,
    "image/bmp": DocumentType.IMAGE,
    "image/webp": DocumentType.IMAGE,
}

EXT_TO_DOCTYPE = {
    ".pdf": DocumentType.PDF,
    ".xlsx": DocumentType.EXCEL,
    ".xls": DocumentType.EXCEL,
    ".xlsm": DocumentType.EXCEL,
    ".csv": DocumentType.CSV,
    ".docx": DocumentType.DOCX,
    ".doc": DocumentType.DOCX,
    ".png": DocumentType.IMAGE,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
    ".tiff": DocumentType.IMAGE,
    ".tif": DocumentType.IMAGE,
    ".bmp": DocumentType.IMAGE,
    ".webp": DocumentType.IMAGE,
}


def get_document_type(filename: str, mime_type: str | None = None) -> DocumentType:
    if mime_type and mime_type in MIME_TO_DOCTYPE:
        return MIME_TO_DOCTYPE[mime_type]
    ext = Path(filename).suffix.lower()
    return EXT_TO_DOCTYPE.get(ext, DocumentType.UNKNOWN)


def generate_unique_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix
    return f"{uuid.uuid4().hex}{ext}"


def safe_file_path(upload_dir: str, filename: str) -> str:
    return os.path.join(upload_dir, filename)


def human_readable_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
