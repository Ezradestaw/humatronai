import os
import re
from typing import Tuple
from core.config import settings

# Academic email domains
ACADEMIC_DOMAIN_PATTERNS = [
    r"\.edu$",
    r"\.edu\.[a-z]{2}$",    # e.g. .edu.et
    r"\.ac\.[a-z]{2}$",     # e.g. .ac.uk, .ac.za
    r"aau\.edu\.et$",       # Addis Ababa University
    r"astu\.edu\.et$",      # Adama Science and Technology
    r"aastu\.edu\.et$",     # Addis Ababa Science and Technology
]

PDF_MAGIC_BYTES = b"%PDF-"

def sanitize_filename(filename: str) -> str:
    """Strip dangerous path traversal characters and return safe basename."""
    clean = os.path.basename(filename)
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    if not clean.lower().endswith(".pdf"):
        clean += ".pdf"
    return clean

def validate_pdf_data(data: bytes) -> Tuple[bool, str]:
    """
    Validate PDF byte payload:
    1. Size limit
    2. Magic byte header (%PDF-)
    """
    max_bytes = settings.max_pdf_size_mb * 1024 * 1024
    if len(data) == 0:
        return False, "Uploaded file is empty."
    
    if len(data) > max_bytes:
        return False, f"File exceeds maximum allowed size of {settings.max_pdf_size_mb} MB."
    
    # Check for PDF magic bytes within the first 1024 bytes (some PDFs have leading BOM/comments)
    if PDF_MAGIC_BYTES not in data[:1024]:
        return False, "Invalid file format: Header does not match standard PDF specification."
        
    return True, "Valid"

def is_academic_email(email: str) -> bool:
    """Check if an email address belongs to an accredited university or college."""
    email = email.strip().lower()
    if "@" not in email:
        return False
    domain = email.split("@")[-1]
    
    for pattern in ACADEMIC_DOMAIN_PATTERNS:
        if re.search(pattern, domain):
            return True
    return False
