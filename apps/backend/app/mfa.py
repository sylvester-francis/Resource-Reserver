"""Multi-Factor Authentication (MFA) functionality using TOTP."""

import base64
import io
import json
import secrets

import pyotp
import qrcode
from sqlalchemy.orm import Session

from app import models
from app.auth import hash_password, verify_password


def generate_mfa_secret() -> str:
    """Generate a new MFA secret for TOTP."""
    return pyotp.random_base32()


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes for MFA recovery."""
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric codes
        code = secrets.token_hex(4).upper()
        codes.append(code)
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    """Hash backup codes before storing."""
    return [hash_password(code) for code in codes]


def verify_backup_code(code: str, hashed_codes: list[str]) -> bool:
    """Verify a backup code against hashed codes."""
    for hashed in hashed_codes:
        if verify_password(code, hashed):
            return True
    return False


def setup_mfa(user: models.User, db: Session) -> dict:
    """
    Set up MFA for a user.

    Returns:
        Dictionary with secret, QR code, and backup codes
    """
    # Generate secret
    secret = generate_mfa_secret()

    # Generate TOTP URI for QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username, issuer_name="Resource Reserver"
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for easy transport
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Generate backup codes
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)

    # Store secret (temporarily, until verified)
    user.mfa_secret = secret
    user.mfa_backup_codes = json.dumps(hashed_codes)
    user.mfa_enabled = False  # Not enabled until verified
    db.commit()

    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code_base64}",
        "backup_codes": backup_codes,  # Show once, then hash
        "totp_uri": totp_uri,
    }


def verify_mfa(user: models.User, code: str) -> bool:
    """
    Verify a TOTP code for MFA.

    Args:
        user: User to verify
        code: 6-digit TOTP code

    Returns:
        True if code is valid, False otherwise
    """
    if not user.mfa_secret:
        return False

    totp = pyotp.TOTP(user.mfa_secret)
    # valid_window=1 allows for 30 seconds of clock skew
    return totp.verify(code, valid_window=1)


def enable_mfa(user: models.User, code: str, db: Session) -> bool:
    """
    Enable MFA for user after verifying the setup code.

    Args:
        user: User to enable MFA for
        code: Verification code from authenticator app
        db: Database session

    Returns:
        True if enabled successfully, False if code invalid
    """
    if not verify_mfa(user, code):
        return False

    user.mfa_enabled = True
    db.commit()
    return True


def disable_mfa(user: models.User, password: str, db: Session) -> bool:
    """
    Disable MFA for user (requires password confirmation).

    Args:
        user: User to disable MFA for
        password: User's password for confirmation
        db: Database session

    Returns:
        True if disabled successfully, False if password invalid
    """
    if not verify_password(password, user.hashed_password):
        return False

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    db.commit()
    return True


def use_backup_code(user: models.User, code: str, db: Session) -> bool:
    """
    Use a backup code for MFA.

    Args:
        user: User attempting backup code
        code: Backup code
        db: Database session

    Returns:
        True if code is valid and used, False otherwise
    """
    if not user.mfa_backup_codes:
        return False

    # Load hashed codes
    hashed_codes = json.loads(user.mfa_backup_codes)

    # Check if code is valid
    code_index = None
    for i, hashed in enumerate(hashed_codes):
        if verify_password(code, hashed):
            code_index = i
            break

    if code_index is None:
        return False

    # Remove used code
    hashed_codes.pop(code_index)
    user.mfa_backup_codes = json.dumps(hashed_codes)
    db.commit()

    return True


def regenerate_backup_codes(user: models.User, db: Session) -> list[str]:
    """
    Regenerate backup codes for user.

    Args:
        user: User to regenerate codes for
        db: Database session

    Returns:
        New list of backup codes (unhashed, show once)
    """
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)

    user.mfa_backup_codes = json.dumps(hashed_codes)
    db.commit()

    return backup_codes
