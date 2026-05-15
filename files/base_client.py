"""
clients/base_client.py
-----------------------
Shared async HTTP client used by all service clients.
Handles connection pooling, timeout, and maps HTTP error
codes to gateway exceptions that Graphene formats cleanly.

All service clients import get, post, patch, delete from here.
They never instantiate httpx.AsyncClient themselves.
"""

import httpx
import logging
from decouple import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Exceptions — raised by _handle(), caught in resolvers or mutations
# ─────────────────────────────────────────────────────────────────────────────

class GatewayError(Exception):
    """Base class for all gateway HTTP errors."""
    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class NotFoundError(GatewayError):
    """Downstream service returned 404."""
    pass


class ValidationError(GatewayError):
    """Downstream service returned 400 or 422. payload contains field errors."""
    pass


class DuplicateError(GatewayError):
    """Downstream service returned 409. payload contains existing resource."""
    pass


class ServiceUnavailableError(GatewayError):
    """Downstream service returned 5xx or is unreachable."""
    pass


class UnauthorizedError(GatewayError):
    """Downstream service returned 401 or 403."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Single shared async client (reuses TCP connections across requests)
# ─────────────────────────────────────────────────────────────────────────────

TIMEOUT = float(config("SERVICE_TIMEOUT_SECONDS", default=10))

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=5.0,    # seconds to establish TCP connection
        read=TIMEOUT,   # seconds to wait for service to start responding
        write=5.0,
        pool=5.0,
    ),
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Public HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get(url: str, headers: dict = None, params: dict = None) -> dict:
    try:
        response = await _client.get(url, headers=_headers(headers), params=params or {})
        return _handle(response, url)
    except httpx.TimeoutException:
        raise ServiceUnavailableError(f"Timeout calling {url}")
    except httpx.ConnectError:
        raise ServiceUnavailableError(f"Cannot connect to service at {url}")


async def post(url: str, data: dict, headers: dict = None) -> dict:
    try:
        response = await _client.post(url, json=data, headers=_headers(headers))
        return _handle(response, url)
    except httpx.TimeoutException:
        raise ServiceUnavailableError(f"Timeout calling {url}")
    except httpx.ConnectError:
        raise ServiceUnavailableError(f"Cannot connect to service at {url}")


async def patch(url: str, data: dict, headers: dict = None) -> dict:
    try:
        response = await _client.patch(url, json=data, headers=_headers(headers))
        return _handle(response, url)
    except httpx.TimeoutException:
        raise ServiceUnavailableError(f"Timeout calling {url}")
    except httpx.ConnectError:
        raise ServiceUnavailableError(f"Cannot connect to service at {url}")


async def delete(url: str, headers: dict = None) -> dict:
    try:
        response = await _client.delete(url, headers=_headers(headers))
        return _handle(response, url)
    except httpx.TimeoutException:
        raise ServiceUnavailableError(f"Timeout calling {url}")
    except httpx.ConnectError:
        raise ServiceUnavailableError(f"Cannot connect to service at {url}")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _headers(extra: dict = None) -> dict:
    """Merge default gateway headers with per-call extras."""
    base = {"Content-Type": "application/json", "X-Gateway": "true"}
    if extra:
        base.update(extra)
    return base


def _handle(response: httpx.Response, url: str) -> dict:
    """
    Map HTTP status codes to typed exceptions.
    Returns the parsed JSON body on success.
    """
    logger.debug(f"[base_client] {response.request.method} {url} → {response.status_code}")

    if response.status_code in (200, 201, 202):
        # Empty body (e.g. 202 Accepted for async ops) returns {}
        return response.json() if response.content else {}

    if response.status_code == 204:
        return {}

    if response.status_code == 400:
        raise ValidationError(
            "Validation error from downstream service",
            status_code=400,
            payload=response.json(),
        )

    if response.status_code == 401:
        raise UnauthorizedError("Unauthorized", status_code=401)

    if response.status_code == 403:
        raise UnauthorizedError("Forbidden", status_code=403)

    if response.status_code == 404:
        raise NotFoundError("Resource not found", status_code=404)

    if response.status_code == 409:
        # Duplicate — payload contains the existing resource
        # Callers decide whether to treat this as error or success
        raise DuplicateError(
            "Duplicate resource",
            status_code=409,
            payload=response.json(),
        )

    if response.status_code == 422:
        raise ValidationError(
            "Unprocessable entity",
            status_code=422,
            payload=response.json(),
        )

    if response.status_code >= 500:
        logger.error(f"[base_client] Downstream 5xx: {url} → {response.status_code}")
        raise ServiceUnavailableError(
            "Downstream service error",
            status_code=response.status_code,
        )

    # Unexpected status code
    raise GatewayError(
        f"Unexpected status {response.status_code} from {url}",
        status_code=response.status_code,
    )
