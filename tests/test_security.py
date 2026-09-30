import pytest
import time
from core.utils.security import create_signed_token, verify_signed_token, hash_file_bytes
from core.utils.validators import sanitize_filename, validate_pdf_data, is_academic_email

def test_signed_token_creation_and_verification():
    tg_id = 987654321
    token = create_signed_token(telegram_id=tg_id, expires_in_seconds=600)
    assert token is not None
    assert len(token.split(".")) == 4

    is_valid, decoded_id, reason = verify_signed_token(token)
    assert is_valid is True
    assert decoded_id == tg_id
    assert reason == "Valid"

def test_tampered_token_rejection():
    tg_id = 123456789
    token = create_signed_token(telegram_id=tg_id, expires_in_seconds=600)
    parts = token.split(".")
    # Tamper with the telegram ID
    tampered = f"999999999.{parts[1]}.{parts[2]}.{parts[3]}"
    is_valid, _, reason = verify_signed_token(tampered)
    assert is_valid is False
    assert "signature" in reason.lower()

def test_expired_token_rejection():
    tg_id = 123456789
    token = create_signed_token(telegram_id=tg_id, expires_in_seconds=-10)
    is_valid, _, reason = verify_signed_token(token)
    assert is_valid is False
    assert "expired" in reason.lower()

def test_path_traversal_sanitization():
    unsafe_filename = "../../../etc/passwd"
    safe = sanitize_filename(unsafe_filename)
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe
    assert safe.endswith(".pdf")
    assert safe == "passwd.pdf"

    windows_traversal = "..\\..\\Windows\\System32\\cmd.exe"
    safe_win = sanitize_filename(windows_traversal)
    assert ".." not in safe_win
    assert safe_win.endswith(".pdf")

def test_pdf_magic_bytes_validation():
    # Valid PDF header
    valid_pdf_content = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    is_valid, reason = validate_pdf_data(valid_pdf_content)
    assert is_valid is True

    # Fake PDF (e.g. executable or text file renamed to .pdf)
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00This is an executable binary."
    is_valid, reason = validate_pdf_data(fake_pdf)
    assert is_valid is False
    assert "standard PDF" in reason

def test_academic_email_detection():
    assert is_academic_email("student@harvard.edu") is True
    assert is_academic_email("fikru@aau.edu.et") is True
    assert is_academic_email("researcher@oxford.ac.uk") is True
    assert is_academic_email("user@gmail.com") is False
    assert is_academic_email("spammer@random.com") is False
    assert is_academic_email("invalid-email") is False

def test_file_hash_bytes():
    data = b"Sample Humatron document bytes"
    h1 = hash_file_bytes(data)
    h2 = hash_file_bytes(data)
    assert h1 == h2
    assert len(h1) == 64
