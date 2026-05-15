"""
types.py
---------
All Graphene ObjectType definitions for the gateway schema.

RELATIONSHIP TO DTOs
---------------------
DTOs carry raw data from services (dataclasses).
Types define what the GraphQL client can see and query (Graphene classes).

They are intentionally separate because:
- A DTO may have fields the client should never see (internal flags, raw errors)
- A GraphQL type may have computed or cross-service fields (resolve_payment)
- Renaming a DTO field doesn't break the client-facing schema

CROSS-SERVICE FIELDS
---------------------
Fields that require calling another service are defined here as
graphene.Field(OtherType) with a resolve_* method.
Those resolve methods use DataLoaders from info.context so
multiple orders don't cause N+1 HTTP calls.
"""

import graphene
from .dtos import (
    UserDTO, OrderDTO, OrderItemDTO, ShippingAddressDTO,
    PaymentDTO, ShipmentDTO, ReservationDTO, StockLevelDTO,
    NotificationDTO, QueueStatsDTO, DLQMessageDTO,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared / embedded types
# ─────────────────────────────────────────────────────────────────────────────

class OrderItemType(graphene.ObjectType):
    sku          = graphene.String()
    quantity     = graphene.Int()
    unit_price   = graphene.Int()
    subtotal     = graphene.Int()
    product_name = graphene.String()

    @classmethod
    def from_dto(cls, dto: OrderItemDTO):
        return cls(
            sku=dto.sku,
            quantity=dto.quantity,
            unit_price=dto.unit_price,
            subtotal=dto.subtotal,
            product_name=dto.product_name,
        )


class ShippingAddressType(graphene.ObjectType):
    street = graphene.String()
    city = graphene.String()
    country = graphene.String()
    region          = graphene.String()
    postal_code     = graphene.String()
    recipient_name  = graphene.String()
    recipient_phone = graphene.String()

    @classmethod
    def from_dto(cls, dto: ShippingAddressDTO):
        if dto is None:
            return None
        return cls(**dto.__dict__)


# ─────────────────────────────────────────────────────────────────────────────
# Payment type
# ─────────────────────────────────────────────────────────────────────────────

class PaymentType(graphene.ObjectType):
    id                = graphene.ID()
    order_id          = graphene.ID()
    status            = graphene.String()   # success | failed | refunded | pending
    currency          = graphene.String()
    amount_charged    = graphene.Int()
    payment_intent_id = graphene.String()
    error_code        = graphene.String()
    refund_id         = graphene.String()
    refunded_amount   = graphene.Int()
    created_at        = graphene.String()

    @classmethod
    def from_dto(cls, dto: PaymentDTO):
        if dto is None:
            return None
        return cls(**{k: v for k, v in dto.__dict__.items() if hasattr(cls, k)})


# ─────────────────────────────────────────────────────────────────────────────
# Shipment type
# ─────────────────────────────────────────────────────────────────────────────

class ShipmentType(graphene.ObjectType):
    id                      = graphene.ID()
    order_id                = graphene.ID()
    status                  = graphene.String()
    tracking_number         = graphene.String()
    carrier                 = graphene.String()
    estimated_delivery_days = graphene.Int()
    dispatched_at           = graphene.String()
    delivered_at            = graphene.String()
    shipping_address        = graphene.Field(ShippingAddressType)

    @classmethod
    def from_dto(cls, dto: ShipmentDTO):
        if dto is None:
            return None
        address = ShippingAddressType.from_dto(dto.shipping_address)
        return cls(
            id=dto.id,
            order_id=dto.order_id,
            status=dto.status,
            tracking_number=dto.tracking_number,
            carrier=dto.carrier,
            estimated_delivery_days=dto.estimated_delivery_days,
            dispatched_at=dto.dispatched_at,
            delivered_at=dto.delivered_at,
            shipping_address=address,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Order type — resolves payment and shipment lazily via DataLoader
# ─────────────────────────────────────────────────────────────────────────────

class OrderType(graphene.ObjectType):
    id                = graphene.ID()
    user_id           = graphene.ID()
    status            = graphene.String()
    currency          = graphene.String()
    total_amount      = graphene.Int()
    amount_charged    = graphene.Int()
    error_code        = graphene.String()
    error_message     = graphene.String()
    idempotency_key   = graphene.String()
    created_at        = graphene.String()
    updated_at        = graphene.String()
    items             = graphene.List(OrderItemType)
    shipping_address  = graphene.Field(ShippingAddressType)

    # Cross-service fields — resolved via DataLoader (no N+1)
    payment  = graphene.Field(PaymentType)
    shipment = graphene.Field(ShipmentType)

    async def resolve_payment(self, info):
        """
        Uses PaymentLoader from context.
        All resolve_payment calls in one request are batched into
        one GET /payments/?order_ids=... call.
        """
        loader = info.context.payment_loader
        if loader is None:
            return None
        dto = await loader.load(self.id)
        return PaymentType.from_dto(dto)

    async def resolve_shipment(self, info):
        loader = info.context.shipment_loader
        if loader is None:
            return None
        dto = await loader.load(self.id)
        return ShipmentType.from_dto(dto)

    @classmethod
    def from_dto(cls, dto: OrderDTO):
        items = [OrderItemType.from_dto(i) for i in (dto.items or [])]
        address = ShippingAddressType.from_dto(dto.shipping_address)
        return cls(
            id=dto.id,
            user_id=dto.user_id,
            status=dto.status,
            currency=dto.currency,
            total_amount=dto.total_amount,
            amount_charged=dto.amount_charged,
            error_code=dto.error_code,
            error_message=dto.error_message,
            idempotency_key=dto.idempotency_key,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            items=items,
            shipping_address=address,
        )


# ─────────────────────────────────────────────────────────────────────────────
# User type — resolves orders lazily (cross-service)
# ─────────────────────────────────────────────────────────────────────────────

class UserType(graphene.ObjectType):
    id          = graphene.ID()
    username    = graphene.String()
    email       = graphene.String()
    phone       = graphene.String()
    profile_pic = graphene.String()
    created_at  = graphene.String()

    # Cross-service: orders live in Order Service, not Account Service
    orders = graphene.List(OrderType)

    async def resolve_orders(self, info):
        """
        If orders were pre-fetched in the parent resolver (e.g. resolve_me
        used asyncio.gather), they're on _prefetched_orders and we skip
        the extra HTTP call.
        """
        if hasattr(self, "_prefetched_orders") and self._prefetched_orders is not None:
            return self._prefetched_orders

        from files.service_clients import order_client
        dtos = await order_client.list_orders(self.id)
        return [OrderType.from_dto(d) for d in dtos]

    @classmethod
    def from_dto(cls, dto: UserDTO):
        return cls(
            id=dto.id,
            username=dto.username,
            email=dto.email,
            phone=dto.phone,
            profile_pic=dto.profile_pic,
            created_at=dto.created_at,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Inventory types
# ─────────────────────────────────────────────────────────────────────────────

class StockLevelType(graphene.ObjectType):
    sku       = graphene.String()
    available = graphene.Int()
    reserved  = graphene.Int()
    total     = graphene.Int()

    @classmethod
    def from_dto(cls, dto: StockLevelDTO):
        return cls(**dto.__dict__)


class ReservationType(graphene.ObjectType):
    id             = graphene.ID()
    order_id       = graphene.ID()
    status         = graphene.String()
    reservation_id = graphene.String()
    reserved_at    = graphene.String()
    released_at    = graphene.String()

    @classmethod
    def from_dto(cls, dto: ReservationDTO):
        return cls(
            id=dto.id,
            order_id=dto.order_id,
            status=dto.status,
            reservation_id=dto.reservation_id,
            reserved_at=dto.reserved_at,
            released_at=dto.released_at,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Notification type
# ─────────────────────────────────────────────────────────────────────────────

class NotificationType(graphene.ObjectType):
    id         = graphene.ID()
    order_id   = graphene.ID()
    channel    = graphene.String()    # email | sms
    event_type = graphene.String()
    status     = graphene.String()
    recipient  = graphene.String()
    subject    = graphene.String()
    sent_at    = graphene.String()

    @classmethod
    def from_dto(cls, dto: NotificationDTO):
        return cls(**{k: v for k, v in dto.__dict__.items() if hasattr(cls, k)})


# ─────────────────────────────────────────────────────────────────────────────
# Debug types (development only)
# ─────────────────────────────────────────────────────────────────────────────

class QueueStatsType(graphene.ObjectType):
    name      = graphene.String()
    messages  = graphene.Int()
    consumers = graphene.Int()
    durable   = graphene.Boolean()

    @classmethod
    def from_dto(cls, dto: QueueStatsDTO):
        return cls(
            name=dto.name,
            messages=dto.messages,
            consumers=dto.consumers,
            durable=dto.durable,
        )


class DLQMessageType(graphene.ObjectType):
    order_id       = graphene.ID()
    death_reason   = graphene.String()
    retry_count    = graphene.Int()
    original_queue = graphene.String()
    first_death_at = graphene.String()

    @classmethod
    def from_dto(cls, dto: DLQMessageDTO):
        return cls(**{k: v for k, v in dto.__dict__.items() if hasattr(cls, k)})


# ─────────────────────────────────────────────────────────────────────────────
# Mutation result types
# ─────────────────────────────────────────────────────────────────────────────

class CreateOrderResultType(graphene.ObjectType):
    """
    Returned by createOrder mutation.
    Always succeeds at the HTTP level — caller checks success flag.
    This avoids Graphene raising exceptions for business-logic failures
    (duplicate orders, validation errors) which pollute the errors array.
    """
    success    = graphene.Boolean(required=True)
    order      = graphene.Field(OrderType)
    duplicate  = graphene.Boolean()
    error_code = graphene.String()
    message    = graphene.String()


class CancelOrderResultType(graphene.ObjectType):
    success = graphene.Boolean(required=True)
    message = graphene.String()


class RefundResultType(graphene.ObjectType):
    success        = graphene.Boolean(required=True)
    refund_id      = graphene.String()
    refunded_amount = graphene.Int()
    message        = graphene.String()
