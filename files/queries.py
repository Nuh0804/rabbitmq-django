"""
queries.py
-----------
All GraphQL Query resolvers.

Each resolver:
1. Checks authentication via info.context.is_authenticated
2. Calls the relevant service client
3. Converts the DTO to a Graphene type
4. Returns the type — Graphene handles serialization

ADDING A NEW QUERY
-------------------
1. Define the field on the Query class: my_field = graphene.Field(SomeType, ...)
2. Write async def resolve_my_field(self, info, ...):
3. Call the service client, convert DTO → Type, return
That's it. No other file needs to change unless the DTO/Type is new.
"""

import asyncio
import graphene
from ..gateway.gateway.types import (
    UserType, OrderType, PaymentType, ShipmentType,
    StockLevelType, ReservationType, NotificationType,
    QueueStatsType, DLQMessageType,
)
from files.service_clients import (
    account_client, order_client, payment_client,
    inventory_client, shipping_client, notification_client,
)
from files.base_client import NotFoundError, UnauthorizedError, GatewayError
import logging

logger = logging.getLogger(__name__)


def require_auth(info):
    """Helper — raises if the request is not authenticated."""
    if not info.context.is_authenticated:
        raise UnauthorizedError("Authentication required")


class Query(graphene.ObjectType):

    # ── User / Account ────────────────────────────────────────────────────────

    me = graphene.Field(
        UserType,
        description="Get the authenticated user's profile and orders in one call.",
    )

    user = graphene.Field(
        UserType,
        id=graphene.ID(required=True),
        description="Get a user by ID (admin use).",
    )

    async def resolve_me(self, info):
        """
        Fetches user profile AND orders in parallel (asyncio.gather).
        Orders are pre-attached so resolve_orders skips the extra HTTP call.
        Payment and shipment are resolved lazily via DataLoader only if
        the client requested those fields.
        """
        require_auth(info)
        user_id = info.context.user_id

        # Fire both calls simultaneously
        user_dto, order_dtos = await asyncio.gather(
            account_client.get_me(user_id),
            order_client.list_orders(user_id),
        )

        user_type = UserType.from_dto(user_dto)
        # Pre-attach orders so resolve_orders won't make another HTTP call
        user_type._prefetched_orders = [OrderType.from_dto(o) for o in order_dtos]
        return user_type

    async def resolve_user(self, info, id):
        require_auth(info)
        try:
            dto = await account_client.get_user(id)
            return UserType.from_dto(dto)
        except NotFoundError:
            return None

    # ── Orders ────────────────────────────────────────────────────────────────

    order = graphene.Field(
        OrderType,
        id=graphene.ID(required=True),
        description="Get a single order by ID.",
    )

    my_orders = graphene.List(
        OrderType,
        description="Get all orders for the authenticated user.",
    )

    async def resolve_order(self, info, id):
        require_auth(info)
        try:
            dto = await order_client.get_order(id, info.context.user_id)
            return OrderType.from_dto(dto)
        except NotFoundError:
            return None

    async def resolve_my_orders(self, info):
        require_auth(info)
        dtos = await order_client.list_orders(info.context.user_id)
        return [OrderType.from_dto(d) for d in dtos]

    # ── Payments ──────────────────────────────────────────────────────────────

    payment = graphene.Field(
        PaymentType,
        order_id=graphene.ID(required=True),
        description="Get payment details for an order.",
    )

    async def resolve_payment(self, info, order_id):
        require_auth(info)
        try:
            dto = await payment_client.get_payment(order_id, info.context.user_id)
            return PaymentType.from_dto(dto)
        except NotFoundError:
            return None

    # ── Inventory ─────────────────────────────────────────────────────────────

    stock_level = graphene.Field(
        StockLevelType,
        sku=graphene.String(required=True),
        description="Check current stock level for a SKU.",
    )

    reservation = graphene.Field(
        ReservationType,
        order_id=graphene.ID(required=True),
        description="Get the inventory reservation for an order.",
    )

    async def resolve_stock_level(self, info, sku):
        require_auth(info)
        try:
            dto = await inventory_client.get_stock_level(sku, info.context.user_id)
            return StockLevelType.from_dto(dto)
        except NotFoundError:
            return None

    async def resolve_reservation(self, info, order_id):
        require_auth(info)
        try:
            dto = await inventory_client.get_reservation(order_id, info.context.user_id)
            return ReservationType.from_dto(dto)
        except NotFoundError:
            return None

    # ── Shipping ──────────────────────────────────────────────────────────────

    shipment = graphene.Field(
        ShipmentType,
        order_id=graphene.ID(required=True),
        description="Get shipment and tracking info for an order.",
    )

    async def resolve_shipment(self, info, order_id):
        require_auth(info)
        try:
            dto = await shipping_client.get_shipment(order_id, info.context.user_id)
            return ShipmentType.from_dto(dto)
        except NotFoundError:
            return None

    # ── Notifications ─────────────────────────────────────────────────────────

    notifications = graphene.List(
        NotificationType,
        order_id=graphene.ID(),
        channel=graphene.String(),
        event_type=graphene.String(),
        description="List notifications sent for an order.",
    )

    async def resolve_notifications(self, info, order_id=None, channel=None, event_type=None):
        require_auth(info)
        dtos = await notification_client.list_notifications(
            user_id=info.context.user_id,
            order_id=order_id,
            channel=channel,
            event_type=event_type,
        )
        return [NotificationType.from_dto(d) for d in dtos]

    # ── Debug (development only) ──────────────────────────────────────────────

    queue_stats = graphene.List(
        QueueStatsType,
        description="[DEBUG] RabbitMQ queue depths and consumer counts.",
    )

    dlq_messages = graphene.List(
        DLQMessageType,
        queue_name=graphene.String(required=True),
        description="[DEBUG] Messages sitting in a Dead Letter Queue.",
    )

    async def resolve_queue_stats(self, info):
        require_auth(info)
        from django.conf import settings
        if not settings.DEBUG:
            raise GatewayError("Debug endpoints are disabled in production")
        dtos = await order_client.get_debug_queues()
        return [QueueStatsType.from_dto(d) for d in dtos]

    async def resolve_dlq_messages(self, info, queue_name):
        require_auth(info)
        from django.conf import settings
        if not settings.DEBUG:
            raise GatewayError("Debug endpoints are disabled in production")
        dtos = await payment_client.get_dlq(queue_name)
        return [DLQMessageType.from_dto(d) for d in dtos]
