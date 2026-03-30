import secrets
import string
from datetime import datetime, timedelta, timezone

def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically secure numeric OTP.
    """
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))

def get_otp_expiry(minutes: int = 5):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def is_otp_expired(expires_at):
    if not expires_at:
        return True

    # Firestore timestamps usually support comparison directly after conversion
    if hasattr(expires_at, "replace") and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) > expires_at