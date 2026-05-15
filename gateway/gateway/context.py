"""
context.py
-----------
Builds the GraphQL context object once per request.

Every resolver receives this via info.context.
It carries:
    - user_id: the authenticated user (or None for public queries)
    - DataLoader instances (fresh per request — prevents cross-request leaks)
    - the raw Django request (for headers, IP, etc.)

WIRING IN urls.py
------------------
    from graphene_django.views import GraphQLView
    from .schema import schema
    from .context import build_context

    urlpatterns = [
        path("graphql/", GraphQLView.as_view(schema=schema, get_context=build_context)),
    ]
"""

from dataclasses import dataclass, field
from typing import Optional
from django.http import HttpRequest
from .auth import verify_jwt, AuthError
from .dataloaders.loaders import PaymentLoader, ShipmentLoader, UserLoader
import logging

logger = logging.getLogger(__name__)


@dataclass
class GatewayContext:
    """
    The context object every resolver receives via info.context.

    Usage in a resolver:
        async def resolve_order(self, info, id):
            user_id = info.context.user_id      # authenticated user
            loader  = info.context.payment_loader
            ...
    """
    request: HttpRequest
    user_id: Optional[str]              # None if request is unauthenticated
    is_authenticated: bool

    # DataLoaders — one instance per request, shared across all resolvers
    # in that request so batching works correctly
    payment_loader: Optional[PaymentLoader] = field(default=None, repr=False)
    shipment_loader: Optional[ShipmentLoader] = field(default=None, repr=False)
    user_loader: Optional[UserLoader] = field(default=None, repr=False)

    # Correlation ID for distributed tracing — passed through to service calls
    correlation_id: Optional[str] = None


def build_context(request: HttpRequest) -> GatewayContext:
    """
    Called by Graphene on every incoming request.
    Extracts user from JWT and creates per-request DataLoader instances.

    Public queries (no Authorization header) get is_authenticated=False
    and user_id=None. Resolvers that require auth use the
    @login_required decorator in permissions.py.
    """
    user_id = None
    is_authenticated = False

    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header:
        try:
            user_id = verify_jwt(auth_header)
            is_authenticated = True
        except AuthError as e:
            # Don't raise here — let the resolver's permission check handle it
            # so public queries can still proceed unauthenticated
            logger.debug(f"[context] Auth failed: {e}")

    # Correlation ID — use incoming header or generate one
    import uuid
    correlation_id = (
        request.META.get("HTTP_X_CORRELATION_ID")
        or str(uuid.uuid4())
    )

    # DataLoaders receive user_id so they can pass X-User-ID to services
    payment_loader  = PaymentLoader(user_id=user_id) if user_id else None
    shipment_loader = ShipmentLoader(user_id=user_id) if user_id else None
    user_loader     = UserLoader(requester_id=user_id) if user_id else None

    return GatewayContext(
        request=request,
        user_id=user_id,
        is_authenticated=is_authenticated,
        payment_loader=payment_loader,
        shipment_loader=shipment_loader,
        user_loader=user_loader,
        correlation_id=correlation_id,
    )
