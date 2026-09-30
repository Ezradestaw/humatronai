import hmac
import hashlib
import secrets
import time
from typing import Tuple
from core.config import settings

def generate_random_token(length: int = 32) -> str:
    """Generate a cryptographically secure random hexadecimal token."""
    return secrets.token_hex(length)

def create_signed_token(telegram_id: int, expires_in_seconds: int = 600) -> str:
    """
    Create a secure, tamper-proof, timestamped linking token.
    Format: <telegram_id>.<expiry_epoch>.<nonce>.<hmac_signature>
    """
    expiry = int(time.time()) + expires_in_seconds
    nonce = secrets.token_hex(8)
    payload = f"{telegram_id}.{expiry}.{nonce}"
    signature = hmac.new(
        settings.humatron_secret_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"

def verify_signed_token(signed_token: str) -> Tuple[bool, int, str]:
    """
    Verify the cryptographic signature and expiration of a linking token.
    Returns: (is_valid, telegram_id, reason)
    """
    try:
        parts = signed_token.split(".")
        if len(parts) != 4:
            return False, 0, "Invalid token format"
        
        telegram_id_str, expiry_str, nonce, signature = parts
        payload = f"{telegram_id_str}.{expiry_str}.{nonce}"
        
        expected_sig = hmac.new(
            settings.humatron_secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature):
            return False, 0, "Tampered or invalid token signature"
            
        expiry = int(expiry_str)
        if time.time() > expiry:
            return False, 0, "Token has expired"
            
        return True, int(telegram_id_str), "Valid"
    except Exception as e:
        return False, 0, f"Token verification error: {str(e)}"

def hash_file_bytes(data: bytes) -> str:
    """Generate SHA-256 hash for document integrity and tracking."""
    return hashlib.sha256(data).hexdigest()
