"""
dtos.py
-------
Data Transfer Objects (DTOs) for the API Gateway.

Each DTO mirrors the exact JSON shape returned by a downstream service's
REST endpoint. Their only job is to carry data from an HTTP response into
the gateway — no business logic lives here.

RULE: a DTO field corresponds to a key in the service's JSON response.
If Order Service returns {"order_id": "...", "status": "..."},
your DTO has order_id and status. The Graphene type may rename or
reshape these — the DTO never does.

ADDING NEW FIELDS
------------------
When a service adds a new field to its response, add it here as
Optional with a default of None. Existing consumers keep working.
When a service adds a new endpoint, add a new DTO class here.
See the answer at the bottom of this file about when you MUST update.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Account Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UserDTO:
    """
    Mirrors: GET /api/users/{id}/
    Mirrors: GET /api/users/me/
    """
    id: str
    username: str
    email: str
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    created_at: Optional[str] = None
    is_active: Optional[bool] = True


@dataclass
class UserListDTO:
    """
    Mirrors: GET /api/users/?ids=1,2,3   (batch fetch for DataLoader)
    """
    results: List[UserDTO] = field(default_factory=list)
    count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Order Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderItemDTO:
    """Single line item inside an order."""
    sku: str
    quantity: int
    unit_price: int
    subtotal: Optional[int] = None
    product_name: Optional[str] = None


@dataclass
class ShippingAddressDTO:
    street: str
    city: str
    country: str
    region: Optional[str] = None
    postal_code: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None


@dataclass
class OrderDTO:
    """
    Mirrors: GET /api/orders/{id}/
    Mirrors: POST /api/orders/  (response body)
    """
    id: str
    user_id: str
    status: str                          # pending | payment_processing | paid |
                                         # fulfilling | shipped | cancelled |
                                         # payment_failed | fulfillment_failed
    currency: str
    total_amount: int
    items: List[OrderItemDTO] = field(default_factory=list)
    shipping_address: Optional[ShippingAddressDTO] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    idempotency_key: Optional[str] = None
    inventory_reserved: Optional[bool] = None
    amount_charged: Optional[int] = None
    payment_intent_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class OrderListDTO:
    """
    Mirrors: GET /api/orders/?user_id=...
    """
    results: List[OrderDTO] = field(default_factory=list)
    count: int = 0
    next: Optional[str] = None
    previous: Optional[str] = None


@dataclass
class CreateOrderResponseDTO:
    """
    Mirrors: POST /api/orders/ — 201 or 409 response.
    409 (duplicate) returns this same shape with duplicate=True.
    """
    id: str
    status: str
    total_amount: int
    currency: str
    duplicate: Optional[bool] = False
    idempotency_key: Optional[str] = None
    created_at: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Payment Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PaymentDTO:
    """
    Mirrors: GET /api/payments/{id}/
    Mirrors: GET /api/payments/?order_id=...
    """
    id: str
    order_id: str
    status: str                          # success | failed | refunded | pending
    currency: str
    amount_charged: Optional[int] = None
    payment_intent_id: Optional[str] = None
    error_code: Optional[str] = None
    refund_id: Optional[str] = None
    refunded_amount: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class PaymentBatchDTO:
    """
    Mirrors: GET /api/payments/?order_ids=id1,id2,id3
    Used by PaymentLoader to batch-fetch payments for multiple orders.
    """
    results: List[PaymentDTO] = field(default_factory=list)


@dataclass
class RefundResponseDTO:
    """
    Mirrors: POST /api/orders/{id}/refund/
    """
    refund_id: str
    status: str                          # refunded | pending
    amount: int
    order_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StockLevelDTO:
    """
    Mirrors: GET /api/stock/{sku}/
    """
    sku: str
    available: int
    reserved: int
    total: int


@dataclass
class ReservationDTO:
    """
    Mirrors: GET /api/reservations/{order_id}/
    """
    id: str
    order_id: str
    status: str                          # reserved | released | dispatched | expired
    reservation_id: Optional[str] = None
    items: Optional[List[dict]] = field(default_factory=list)
    reserved_at: Optional[str] = None
    released_at: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Shipping Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ShipmentDTO:
    """
    Mirrors: GET /api/shipments/{order_id}/
    """
    id: str
    order_id: str
    status: str                          # pending | created | in_transit |
                                         # delivered | cancelled | failed
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    estimated_delivery_days: Optional[int] = None
    shipping_address: Optional[ShippingAddressDTO] = None
    dispatched_at: Optional[str] = None
    delivered_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class ShipmentBatchDTO:
    """
    Mirrors: GET /api/shipments/?order_ids=id1,id2,id3
    Used by ShipmentLoader to batch-fetch shipments for multiple orders.
    """
    results: List[ShipmentDTO] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Notification Service DTOs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NotificationDTO:
    """
    Mirrors: GET /api/notifications/?order_id=...
    """
    id: str
    order_id: str
    channel: str                         # email | sms
    event_type: str                      # payment.succeeded | shipment.created | ...
    status: str                          # delivered | skipped_duplicate | failed
    recipient: str
    subject: Optional[str] = None
    sent_at: Optional[str] = None


@dataclass
class NotificationListDTO:
    """
    Mirrors: GET /api/notifications/?order_id=...&channel=email
    """
    results: List[NotificationDTO] = field(default_factory=list)
    count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Debug / internal DTOs (development only — guarded by DEBUG=True in views)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QueueStatsDTO:
    """
    Mirrors: GET /api/debug/queues/  (any service)
    Wraps the RabbitMQ Management API response.
    """
    name: str
    messages: int
    consumers: int
    durable: bool
    message_stats: Optional[dict] = None
    consumer_details: Optional[List[dict]] = field(default_factory=list)


@dataclass
class DLQMessageDTO:
    """
    Mirrors: GET /api/debug/dlq/{queue_name}/
    """
    order_id: str
    death_reason: str
    retry_count: int
    original_queue: str
    payload: Optional[dict] = None
    first_death_at: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# DTO factory helpers
# ─────────────────────────────────────────────────────────────────────────────

def order_dto_from_dict(data: dict) -> OrderDTO:
    """
    Converts a raw dict (from httpx response.json()) to an OrderDTO.
    Handles nested objects so callers don't have to.
    """
    items = [
        OrderItemDTO(**{k: v for k, v in item.items() if k in OrderItemDTO.__dataclass_fields__})
        for item in data.get("items", [])
    ]
    addr_data = data.get("shipping_address")
    address = (
        ShippingAddressDTO(**{k: v for k, v in addr_data.items() if k in ShippingAddressDTO.__dataclass_fields__})
        if addr_data else None
    )
    top_level = {
        k: v for k, v in data.items()
        if k in OrderDTO.__dataclass_fields__ and k not in ("items", "shipping_address")
    }
    return OrderDTO(**top_level, items=items, shipping_address=address)


def payment_dto_from_dict(data: dict) -> PaymentDTO:
    return PaymentDTO(**{k: v for k, v in data.items() if k in PaymentDTO.__dataclass_fields__})


def shipment_dto_from_dict(data: dict) -> ShipmentDTO:
    addr_data = data.get("shipping_address")
    address = (
        ShippingAddressDTO(**{k: v for k, v in addr_data.items() if k in ShippingAddressDTO.__dataclass_fields__})
        if addr_data else None
    )
    top_level = {
        k: v for k, v in data.items()
        if k in ShipmentDTO.__dataclass_fields__ and k != "shipping_address"
    }
    return ShipmentDTO(**top_level, shipping_address=address)


def user_dto_from_dict(data: dict) -> UserDTO:
    return UserDTO(**{k: v for k, v in data.items() if k in UserDTO.__dataclass_fields__})


def notification_dto_from_dict(data: dict) -> NotificationDTO:
    return NotificationDTO(**{k: v for k, v in data.items() if k in NotificationDTO.__dataclass_fields__})
