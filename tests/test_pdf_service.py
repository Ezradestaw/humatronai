import pytest
import io
from pypdf import PdfWriter
from core.services.pdf_service import PDFService

def generate_sample_pdf_bytes(num_pages: int = 2) -> bytes:
    """Helper to create a genuine test PDF buffer."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842) # A4 dimensions
    
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()

def test_inspect_valid_pdf():
    pdf_bytes = generate_sample_pdf_bytes(num_pages=3)
    info = PDFService.inspect_pdf(pdf_bytes, "test_document.pdf")
    assert info["page_count"] == 3
    assert info["size_bytes"] > 0
    assert "test_document.pdf" in info["title"]

def test_inspect_corrupt_pdf_fails():
    corrupt_bytes = b"%PDF-1.4 but corrupt payload"
    with pytest.raises(Exception):
        PDFService.inspect_pdf(corrupt_bytes, "corrupt.pdf")

def test_extract_text_from_blank_pdf():
    pdf_bytes = generate_sample_pdf_bytes(num_pages=1)
    text = PDFService.extract_text(pdf_bytes)
    assert "No extractable text" in text

def test_compress_pdf():
    pdf_bytes = generate_sample_pdf_bytes(num_pages=2)
    compressed, stats = PDFService.compress_pdf(pdf_bytes)
    assert compressed is not None
    assert len(compressed) > 0
    assert stats["pages"] == 2

@pytest.mark.asyncio
async def test_log_processed_document(db_session):
    from core.models import User
    user = User()
    db_session.add(user)
    await db_session.commit()

    pdf_bytes = generate_sample_pdf_bytes(num_pages=1)
    record = await PDFService.log_processed_document(
        session=db_session,
        user_id=user.id,
        original_filename="../../dangerous.pdf",
        data=pdf_bytes,
        operation="compress",
        page_count=1
    )
    assert record.id is not None
    assert record.original_filename == "dangerous.pdf" # Sanitized!
    assert record.operation == "compress"
    assert record.page_count == 1
