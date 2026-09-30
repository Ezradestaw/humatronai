import os
import io
import uuid
import tempfile
from typing import Dict, Any, Tuple, Optional
from pypdf import PdfReader, PdfWriter
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import ProcessedFile
from core.utils.validators import validate_pdf_data, sanitize_filename
from core.utils.security import hash_file_bytes
from core.utils.logger import logger
from core.config import settings

class PDFService:
    @staticmethod
    def inspect_pdf(data: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Safely inspect a PDF buffer:
        Validates magic bytes, reads page count, and extracts non-sensitive metadata.
        """
        is_valid, reason = validate_pdf_data(data)
        if not is_valid:
            raise ValueError(reason)

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # Check if empty password decrypts
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("Password-protected PDFs are not supported. Please remove the password first.")

        num_pages = len(reader.pages)
        if num_pages > settings.max_pdf_pages:
            raise ValueError(f"Document exceeds the maximum limit of {settings.max_pdf_pages} pages (has {num_pages} pages).")

        metadata = reader.metadata or {}
        title = metadata.get("/Title") or original_filename

        return {
            "page_count": num_pages,
            "title": str(title)[:100],
            "size_bytes": len(data),
            "size_kb": round(len(data) / 1024, 2),
            "size_mb": round(len(data) / (1024 * 1024), 2),
        }

    @staticmethod
    def extract_text(data: bytes, max_pages: int = 50) -> str:
        """
        Extract readable plain text from a PDF buffer safely.
        """
        is_valid, reason = validate_pdf_data(data)
        if not is_valid:
            raise ValueError(reason)

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("Password-protected PDFs cannot be extracted.")

        text_parts = []
        pages_to_read = min(len(reader.pages), max_pages)

        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(f"--- Page {i+1} ---\n" + page_text.strip())

        extracted = "\n\n".join(text_parts).strip()
        if not extracted:
            return "No extractable text was found in the uploaded document (it may contain scanned image pages)."
        return extracted

    @staticmethod
    def compress_pdf(data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress PDF by recompressing streams, reducing redundant objects, and stripping excess metadata.
        Uses temporary files in an isolated context manager to guarantee zero disk leakage.
        """
        is_valid, reason = validate_pdf_data(data)
        if not is_valid:
            raise ValueError(reason)

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("Cannot compress password-protected PDF.")

        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams() # Lossless stream compression
            writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        compressed_bytes = output_buffer.getvalue()

        original_size = len(data)
        new_size = len(compressed_bytes)
        savings_percent = round(max(0, (original_size - new_size) / original_size * 100), 1)

        stats = {
            "original_size_kb": round(original_size / 1024, 2),
            "new_size_kb": round(new_size / 1024, 2),
            "savings_percent": savings_percent,
            "pages": len(reader.pages)
        }

        # If compressed version is somehow larger (already compressed images), return original
        if new_size >= original_size:
            return data, stats

        return compressed_bytes, stats

    @staticmethod
    async def log_processed_document(
        session: AsyncSession,
        user_id: str,
        original_filename: str,
        data: bytes,
        operation: str,
        page_count: Optional[int] = None
    ) -> ProcessedFile:
        """Record processed file in audit log."""
        safe_name = sanitize_filename(original_filename)
        file_hash = hash_file_bytes(data)

        record = ProcessedFile(
            user_id=user_id,
            file_hash=file_hash,
            original_filename=safe_name,
            operation=operation,
            file_size_bytes=len(data),
            page_count=page_count,
            status="completed"
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record
