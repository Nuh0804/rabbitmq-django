"""
auth.py
--------
JWT verification at the gateway boundary.

Flow:
    Client sends: Authorization: Bearer <jwt_token>
    Gateway:      verifies signature, extracts user_id
    Services:     receive X-User-ID header, trust it without re-verifying

This means JWT secret/public key is only needed at the gateway.
Individual services don't need the JWT library.

SETUP
------
Add to .env:
    JWT_SECRET=your-secret-key-here          # for HS256 (symmetric)
    JWT_ALGORITHM=HS256

Or for RS256 (asymmetric — production recommended):
    JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...
    JWT_ALGORITHM=RS256

GENERATING A TEST TOKEN (run in Django shell)
----------------------------------------------
    from gateway.auth import create_test_token
    print(create_test_token(user_id="user-001"))
"""

import logging
from jose import jwt, JWTError, ExpiredSignatureError
from decouple import config

logger = logging.getLogger(__name__)

JWT_SECRET    = config("JWT_SECRET", default="dev-secret-change-in-production")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
JWT_AUDIENCE  = config("JWT_AUDIENCE", default=None)


class AuthError(Exception):
    """Raised when token is missing, invalid, or expired."""
    pass


def verify_jwt(authorization_header: str) -> str:
    """
    Verifies the JWT from the Authorization header.
    Returns the user_id (sub claim) on success.
    Raises AuthError on failure.

    Parameters
    ----------
    authorization_header : str
        Value of the Authorization header, e.g. "Bearer eyJhbGc..."
    """
    if not authorization_header:
        raise AuthError("Authorization header missing")

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be 'Bearer <token>'")

    token = parts[1]

    try:
        options = {"verify_aud": bool(JWT_AUDIENCE)}
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            options=options,
        )
    except ExpiredSignatureError:
        raise AuthError("Token has expired")
    except JWTError as e:
        raise AuthError(f"Invalid token: {e}")

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise AuthError("Token payload missing 'sub' or 'user_id' claim")

    logger.debug(f"[auth] Verified token for user_id={user_id}")
    return str(user_id)


def create_test_token(user_id: str, extra_claims: dict = None) -> str:
    """
    Creates a JWT for testing. DO NOT use in production endpoints.

    Usage in Django shell or tests:
        from gateway.auth import create_test_token
        token = create_test_token("user-001")
        # Use as: Authorization: Bearer <token>
    """
    from datetime import datetime, timedelta
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(datetime.timezone.utc),
        "exp": datetime.now(datetime.timezone.utc) + timedelta(hours=24),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
