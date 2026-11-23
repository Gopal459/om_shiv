import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from app.core.config import settings


def hash_otp(otp: str) -> str:
    """Generate SHA-256 hash of plaintext OTP."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    """Verify plaintext OTP against stored SHA-256 hash in constant time."""
    candidate_hash = hash_otp(plain_otp)
    return secrets.compare_digest(candidate_hash, hashed_otp)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode JWT access token with expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
