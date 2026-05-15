"""
mutations.py
-------------
All GraphQL Mutation resolvers.

MUTATION RESULT PATTERN
------------------------
Mutations return a result type (e.g. CreateOrderResultType) instead
of raising GraphQL errors for business-logic failures. This means:
- HTTP status is always 200
- Client checks result.success to know if it worked
- result.error_code tells the client what went wrong
- The GraphQL errors[] array is reserved for unexpected server errors

This is the pattern used by GitHub's GraphQL API and most production
GraphQL APIs. It gives clients predictable error handling.

ADDING A NEW MUTATION
----------------------
1. Define an Input class if needed (inherits graphene.InputObjectType)
2. Define a Mutation class with Arguments + mutate()
3. Register it on the Mutation ObjectType at the bottom
"""

import graphene
from ..gateway.gateway.types import (
    CreateOrderResultType, CancelOrderResultType,
    RefundResultType, OrderType,
)
from .clients.service_clients import order_client, payment_client
from .clients.base_client import ValidationError, GatewayError, UnauthorizedError
import logging

logger = logging.getLogger(__name__)


def require_auth(info):
    if not info.context.is_authenticated:
        raise UnauthorizedError("Authentication required")


# ─────────────────────────────────────────────────────────────────────────────
# Input types
# ─────────────────────────────────────────────────────────────────────────────

class OrderItemInput(graphene.InputObjectType):
    sku        = graphene.String(required=True)
    quantity   = graphene.Int(required=True)
    unit_price = graphene.Int(required=True)


class ShippingAddressInput(graphene.InputObjectType):
    street          = graphene.String(required=True)
    city            = graphene.String(required=True)
    country         = graphene.String(required=True)
    region          = graphene.String()
    postal_code     = graphene.String()
    recipient_name  = graphene.String()
    recipient_phone = graphene.String()
    # Simulator control — pass "service_down", "address_invalid" etc. for testing
    sim_scenario    = graphene.String(default_value="success")


class CreateOrderInput(graphene.InputObjectType):
    items            = graphene.List(graphene.NonNull(OrderItemInput), required=True)
    currency         = graphene.String(required=True)
    card_number      = graphene.String(required=True)
    shipping_address = graphene.Argument(ShippingAddressInput, required=True)
    idempotency_key  = graphene.String()


# ─────────────────────────────────────────────────────────────────────────────
# createOrder
# ─────────────────────────────────────────────────────────────────────────────

class CreateOrder(graphene.Mutation):
    """
    Place a new order. Publishes order.created to RabbitMQ.
    Payment, inventory, shipping, and notification happen asynchronously.

    Returns CreateOrderResultType:
        success    — True if order was created (or already existed)
        order      — the created order object
        duplicate  — True if idempotency_key matched an existing order
        error_code — set if success=False (VALIDATION_ERROR, OUT_OF_STOCK, ...)
        message    — human-readable explanation
    """

    class Arguments:
        input = CreateOrderInput(required=True)

    Output = CreateOrderResultType

    async def mutate(self, info, input):
        require_auth(info)
        user_id = info.context.user_id

        # Convert Graphene input to plain dict for the HTTP client
        payload = {
            "items": [
                {"sku": i.sku, "quantity": i.quantity, "unit_price": i.unit_price}
                for i in input.items
            ],
            "currency": input.currency,
            "card_number": input.card_number,
            "shipping_address": {
                "street": input.shipping_address.street,
                "city": input.shipping_address.city,
                "country": input.shipping_address.country,
                "region": input.shipping_address.region,
                "postal_code": input.shipping_address.postal_code,
                "recipient_name": input.shipping_address.recipient_name,
                "recipient_phone": input.shipping_address.recipient_phone,
                "_sim_scenario": input.shipping_address.sim_scenario,
            },
        }
        if input.idempotency_key:
            payload["idempotency_key"] = input.idempotency_key

        try:
            response_dto = await order_client.create_order(payload, user_id)

            # Fetch the full order to return OrderType (create_order returns minimal DTO)
            order_dto = await order_client.get_order(response_dto.id, user_id)
            order_type = OrderType.from_dto(order_dto)

            return CreateOrderResultType(
                success=True,
                order=order_type,
                duplicate=response_dto.duplicate or False,
                message="Order placed successfully" if not response_dto.duplicate else "Order already exists",
            )

        except ValidationError as e:
            logger.warning(f"[mutations] createOrder validation error: {e.payload}")
            return CreateOrderResultType(
                success=False,
                error_code="VALIDATION_ERROR",
                message=str(e),
            )

        except GatewayError as e:
            logger.error(f"[mutations] createOrder gateway error: {e}")
            return CreateOrderResultType(
                success=False,
                error_code="SERVICE_ERROR",
                message="Order service is unavailable. Please try again.",
            )


# ─────────────────────────────────────────────────────────────────────────────
# cancelOrder
# ─────────────────────────────────────────────────────────────────────────────

class CancelOrder(graphene.Mutation):
    """
    Cancel an order. Publishes order.cancelled to RabbitMQ.
    Payment Service will skip charging if it hasn't run yet.
    If payment already succeeded, use refundOrder instead.
    """

    class Arguments:
        order_id = graphene.ID(required=True)

    Output = CancelOrderResultType

    async def mutate(self, info, order_id):
        require_auth(info)
        try:
            await order_client.cancel_order(order_id, info.context.user_id)
            return CancelOrderResultType(success=True, message="Order cancelled")
        except GatewayError as e:
            return CancelOrderResultType(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# refundOrder
# ─────────────────────────────────────────────────────────────────────────────

class RefundOrder(graphene.Mutation):
    """
    Refund a paid order.
    Triggers payment.refunded event → inventory release → notification.
    """

    class Arguments:
        order_id = graphene.ID(required=True)

    Output = RefundResultType

    async def mutate(self, info, order_id):
        require_auth(info)
        try:
            dto = await payment_client.refund(order_id, info.context.user_id)
            return RefundResultType(
                success=True,
                refund_id=dto.refund_id,
                refunded_amount=dto.amount,
                message="Refund initiated successfully",
            )
        except GatewayError as e:
            return RefundResultType(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# replayDLQ  (debug/ops — guarded by DEBUG=True)
# ─────────────────────────────────────────────────────────────────────────────

class ReplayDLQResult(graphene.ObjectType):
    success  = graphene.Boolean(required=True)
    requeued = graphene.Boolean()
    message  = graphene.String()


class ReplayDLQ(graphene.Mutation):
    """
    [DEBUG] Re-publish a message from a Dead Letter Queue back to its
    original queue. Use after fixing the root cause of the failure.
    Only available when DEBUG=True.
    """

    class Arguments:
        queue_name = graphene.String(required=True)
        order_id   = graphene.ID(required=True)

    Output = ReplayDLQResult

    async def mutate(self, info, queue_name, order_id):
        require_auth(info)
        from django.conf import settings
        if not settings.DEBUG:
            return ReplayDLQResult(
                success=False,
                message="DLQ replay is only available in DEBUG mode",
            )
        try:
            await payment_client.replay_dlq(queue_name, order_id)
            return ReplayDLQResult(success=True, requeued=True, message="Message requeued")
        except GatewayError as e:
            return ReplayDLQResult(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Root Mutation type — register all mutations here
# ─────────────────────────────────────────────────────────────────────────────

class Mutation(graphene.ObjectType):
    create_order = CreateOrder.Field()
    cancel_order = CancelOrder.Field()
    refund_order = RefundOrder.Field()
    replay_dlq   = ReplayDLQ.Field()
