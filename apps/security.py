"""Security module providing password hashing and JWT token handling utilities."""

from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from apps.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize PasswordHash with recommended hasher (Argon2 / Bcrypt)
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plain text password using pwdlib hasher.

    Args:
        password (str): Plain text password to hash.

    Returns:
        str: Cryptographically hashed password string.
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored hash string.

    Args:
        plain_password (str): Plain text candidate password.
        hashed_password (str): Stored hashed password string.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token with an expiration timestamp.

    Args:
        data (dict): Payload data dictionary to encode in the token.
        expires_delta (timedelta | None, optional): Custom expiration duration. Defaults to None.

    Returns:
        str: Encoded JWT string signed with SECRET_KEY.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Args:
        token (str): JWT token string to decode.

    Returns:
        dict | None: Decoded payload dictionary if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
