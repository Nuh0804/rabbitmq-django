"""
clients/base_client.py  (updated for GraphQL services)
--------------------------------------------------------
All downstream services now expose a /graphql/ endpoint.
Every call is an HTTP POST with a JSON body:
    { "query": "...", "variables": {...} }

The response is always:
    { "data": {...}, "errors": [...] }

This module handles:
- Sending GraphQL operations to services
- Extracting data from the response
- Mapping GraphQL errors and HTTP errors to typed exceptions

Nothing in queries.py, mutations.py, types.py, or dtos.py changes.
Only service_clients.py uses this module.
"""

import httpx
import logging
from decouple import config

logger = logging.getLogger(__name__)

TIMEOUT = float(config("SERVICE_TIMEOUT_SECONDS", default=10))

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=TIMEOUT, write=5.0, pool=5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
)


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions (unchanged — gateway resolvers catch these same types)
# ─────────────────────────────────────────────────────────────────────────────

class GatewayError(Exception):
    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}

class NotFoundError(GatewayError): pass
class ValidationError(GatewayError): pass
class DuplicateError(GatewayError): pass
class ServiceUnavailableError(GatewayError): pass
class UnauthorizedError(GatewayError): pass


# ─────────────────────────────────────────────────────────────────────────────
# Core GraphQL caller — used by all service clients
# ─────────────────────────────────────────────────────────────────────────────

async def gql(
    service_url: str,
    query: str,
    variables: dict = None,
    user_id: str = None,
    operation_name: str = None,
) -> dict:
    """
    Send a GraphQL operation to a downstream service.

    Parameters
    ----------
    service_url : str
        Base URL of the service, e.g. "http://order_service:8001"
        The /graphql/ path is appended automatically.
    query : str
        The GraphQL query or mutation string.
    variables : dict
        GraphQL variables matching the operation's variable declarations.
    user_id : str
        Passed as X-User-ID header — services trust this without re-verifying JWT.
    operation_name : str
        Optional — names the operation for logging and service-side tracing.

    Returns
    -------
    dict
        The contents of response["data"] — the actual payload, not the envelope.

    Raises
    ------
    NotFoundError, ValidationError, DuplicateError, ServiceUnavailableError
        Mapped from GraphQL errors[] in the service response.
    """
    endpoint = f"{service_url.rstrip('/')}/graphql/"
    headers = _build_headers(user_id)
    body = {
        "query": query,
        "variables": variables or {},
    }
    if operation_name:
        body["operationName"] = operation_name

    logger.debug(f"[base_client] GQL → {endpoint} op={operation_name or 'anonymous'}")

    try:
        response = await _client.post(endpoint, json=body, headers=headers)
    except httpx.TimeoutException:
        raise ServiceUnavailableError(f"Timeout calling {endpoint}")
    except httpx.ConnectError:
        raise ServiceUnavailableError(f"Cannot connect to service at {endpoint}")

    if response.status_code >= 500:
        logger.error(f"[base_client] HTTP {response.status_code} from {endpoint}")
        raise ServiceUnavailableError(f"Downstream service error ({response.status_code})")

    if response.status_code == 401:
        raise UnauthorizedError("Service returned 401")

    payload = response.json()
    errors = payload.get("errors")
    if errors:
        _raise_from_gql_errors(errors, endpoint)

    data = payload.get("data")
    if data is None:
        raise ServiceUnavailableError(f"Service returned no data field: {endpoint}")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_headers(user_id: str = None) -> dict:
    headers = {"Content-Type": "application/json", "X-Gateway": "true"}
    if user_id:
        headers["X-User-ID"] = str(user_id)
    return headers


def _raise_from_gql_errors(errors: list, endpoint: str):
    """
    Map GraphQL error extensions.code to typed gateway exceptions.

    Services include an extensions.code on their errors:
        { "message": "...", "extensions": { "code": "NOT_FOUND" } }
    """
    first = errors[0]
    message = first.get("message", "Unknown service error")
    extensions = first.get("extensions", {})
    code = extensions.get("code", "").upper()
    payload = extensions.get("payload", {})

    logger.warning(f"[base_client] GQL error from {endpoint}: code={code} msg={message}")

    if code == "NOT_FOUND":
        raise NotFoundError(message, payload=payload)
    if code in ("VALIDATION_ERROR", "BAD_USER_INPUT"):
        raise ValidationError(message, payload=payload)
    if code == "DUPLICATE":
        raise DuplicateError(message, payload=payload)
    if code == "UNAUTHORIZED":
        raise UnauthorizedError(message)

    raise GatewayError(message, payload={"errors": errors})
