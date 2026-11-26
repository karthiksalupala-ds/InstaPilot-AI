import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _get_fernet() -> Fernet:
    """Derive a valid 32-byte URL-safe base64 Fernet key from TOKEN_ENCRYPTION_KEY."""
    raw_key = get_settings().token_encryption_key.encode("utf-8")
    try:
        return Fernet(raw_key)
    except ValueError:
        digest = hashlib.sha256(raw_key).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(plaintext: str) -> str:
    """Encrypt an OAuth access token with a version prefix."""
    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"v1:{token}"


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a versioned OAuth access token."""
    if not ciphertext.startswith("v1:"):
        raise ValueError("Unsupported token ciphertext version")
    payload = ciphertext[3:].encode("utf-8")
    try:
        return _get_fernet().decrypt(payload).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt OAuth token") from exc
