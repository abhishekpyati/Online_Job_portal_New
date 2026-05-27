from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PyPDF2 import PdfReader
from docx import Document

from app.core.config import settings


def upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_upload(file: UploadFile, folder: str, allowed_extensions: set[str]) -> str:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"Unsupported file type. Allowed: {allowed}")
    target_dir = upload_root() / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    target_path = target_dir / filename
    with target_path.open("wb") as buffer:
        buffer.write(file.file.read())
    return str(target_path)


def extract_resume_text(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return ""
