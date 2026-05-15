"""
clients/service_clients.py
---------------------------
One client class per downstream service.
Each method maps to one REST endpoint on that service.

HOW TO ADD A NEW ENDPOINT
---------------------------
1. Add the method to the relevant client class below.
2. Add a DTO for its response in dtos.py.
3. Use it in a resolver (queries.py or mutations.py).
You do NOT need to touch any other file.

SERVICE URLS
-------------
Set these in your .env:
    ACCOUNT_SERVICE_URL=http://account_service:8006
    ORDER_SERVICE_URL=http://order_service:8001
    PAYMENT_SERVICE_URL=http://payment_service:8002
    INVENTORY_SERVICE_URL=http://inventory_service:8003
    SHIPPING_SERVICE_URL=http://shipping_service:8005
    NOTIFICATION_SERVICE_URL=http://notification_service:8004
"""

from decouple import config
from . import base_client as http
from ..dtos import (
    UserDTO, UserListDTO, user_dto_from_dict,
    OrderDTO, OrderListDTO, CreateOrderResponseDTO, order_dto_from_dict,
    PaymentDTO, PaymentBatchDTO, RefundResponseDTO, payment_dto_from_dict,
    StockLevelDTO, ReservationDTO,
    ShipmentDTO, ShipmentBatchDTO, shipment_dto_from_dict,
    NotificationDTO, NotificationListDTO, notification_dto_from_dict,
    QueueStatsDTO, DLQMessageDTO,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _user_headers(user_id: str) -> dict:
    """
    Gateway passes the authenticated user_id to each service as a header.
    Services trust this header — they do not re-verify the JWT.
    """
    return {"X-User-ID": str(user_id)}


# ─────────────────────────────────────────────────────────────────────────────
# Account Service  (port 8006)
# ─────────────────────────────────────────────────────────────────────────────

_ACCOUNT = config("ACCOUNT_SERVICE_URL", default="http://account_service:8006")


class AccountClient:

    async def get_user(self, user_id: str) -> UserDTO:
        data = await http.get(
            f"{_ACCOUNT}/api/users/{user_id}/",
            headers=_user_headers(user_id),
        )
        return user_dto_from_dict(data)

    async def get_me(self, user_id: str) -> UserDTO:
        data = await http.get(
            f"{_ACCOUNT}/api/users/me/",
            headers=_user_headers(user_id),
        )
        return user_dto_from_dict(data)

    async def get_users_batch(self, user_ids: list, requester_id: str) -> list[UserDTO]:
        """
        Batch fetch for DataLoader.
        Expects service to support: GET /api/users/?ids=1,2,3
        """
        ids_param = ",".join(str(i) for i in user_ids)
        data = await http.get(
            f"{_ACCOUNT}/api/users/",
            headers=_user_headers(requester_id),
            params={"ids": ids_param},
        )
        return [user_dto_from_dict(u) for u in data.get("results", [])]

    async def update_profile(self, user_id: str, payload: dict) -> UserDTO:
        data = await http.patch(
            f"{_ACCOUNT}/api/users/{user_id}/",
            data=payload,
            headers=_user_headers(user_id),
        )
        return user_dto_from_dict(data)


# ─────────────────────────────────────────────────────────────────────────────
# Order Service  (port 8001)
# ─────────────────────────────────────────────────────────────────────────────

_ORDER = config("ORDER_SERVICE_URL", default="http://order_service:8001")


class OrderClient:

    async def get_order(self, order_id: str, user_id: str) -> OrderDTO:
        data = await http.get(
            f"{_ORDER}/api/orders/{order_id}/",
            headers=_user_headers(user_id),
        )
        return order_dto_from_dict(data)

    async def list_orders(self, user_id: str) -> list[OrderDTO]:
        data = await http.get(
            f"{_ORDER}/api/orders/",
            headers=_user_headers(user_id),
            params={"user_id": user_id},
        )
        return [order_dto_from_dict(o) for o in data.get("results", [])]

    async def create_order(self, payload: dict, user_id: str) -> CreateOrderResponseDTO:
        from ..dtos import DuplicateError  # noqa — re-exported for callers
        try:
            data = await http.post(
                f"{_ORDER}/api/orders/",
                data=payload,
                headers=_user_headers(user_id),
            )
            return CreateOrderResponseDTO(**{
                k: v for k, v in data.items()
                if k in CreateOrderResponseDTO.__dataclass_fields__
            })
        except base_client.DuplicateError as e:
            # 409 — order with this idempotency_key already exists
            # Return it as a successful (duplicate) response instead of raising
            return CreateOrderResponseDTO(**{
                k: v for k, v in e.payload.items()
                if k in CreateOrderResponseDTO.__dataclass_fields__
            }, duplicate=True)

    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        await http.delete(
            f"{_ORDER}/api/orders/{order_id}/",
            headers=_user_headers(user_id),
        )
        return True

    async def get_debug_queues(self) -> list[QueueStatsDTO]:
        data = await http.get(f"{_ORDER}/api/debug/queues/")
        return [
            QueueStatsDTO(**{k: v for k, v in q.items() if k in QueueStatsDTO.__dataclass_fields__})
            for q in data.get("queues", [])
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Payment Service  (port 8002)
# ─────────────────────────────────────────────────────────────────────────────

_PAYMENT = config("PAYMENT_SERVICE_URL", default="http://payment_service:8002")


class PaymentClient:

    async def get_payment(self, order_id: str, user_id: str) -> PaymentDTO:
        data = await http.get(
            f"{_PAYMENT}/api/payments/",
            headers=_user_headers(user_id),
            params={"order_id": order_id},
        )
        return payment_dto_from_dict(data)

    async def get_payments_batch(self, order_ids: list, user_id: str) -> list[PaymentDTO]:
        """
        Batch fetch for PaymentLoader.
        Expects: GET /api/payments/?order_ids=id1,id2,id3
        """
        ids_param = ",".join(str(i) for i in order_ids)
        data = await http.get(
            f"{_PAYMENT}/api/payments/",
            headers=_user_headers(user_id),
            params={"order_ids": ids_param},
        )
        return [payment_dto_from_dict(p) for p in data.get("results", [])]

    async def refund(self, order_id: str, user_id: str) -> RefundResponseDTO:
        data = await http.post(
            f"{_ORDER}/api/orders/{order_id}/refund/",
            data={"reason": "customer_request"},
            headers=_user_headers(user_id),
        )
        return RefundResponseDTO(**{
            k: v for k, v in data.items()
            if k in RefundResponseDTO.__dataclass_fields__
        })

    async def get_dlq(self, queue_name: str) -> list[DLQMessageDTO]:
        data = await http.get(f"{_PAYMENT}/api/debug/dlq/{queue_name}/")
        return [
            DLQMessageDTO(**{k: v for k, v in m.items() if k in DLQMessageDTO.__dataclass_fields__})
            for m in data.get("messages", [])
        ]

    async def replay_dlq(self, queue_name: str, order_id: str) -> bool:
        await http.post(
            f"{_PAYMENT}/api/debug/dlq/{queue_name}/replay/",
            data={"order_id": order_id},
        )
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Service  (port 8003)
# ─────────────────────────────────────────────────────────────────────────────

_INVENTORY = config("INVENTORY_SERVICE_URL", default="http://inventory_service:8003")


class InventoryClient:

    async def get_stock_level(self, sku: str, user_id: str) -> StockLevelDTO:
        data = await http.get(
            f"{_INVENTORY}/api/stock/{sku}/",
            headers=_user_headers(user_id),
        )
        return StockLevelDTO(**{k: v for k, v in data.items() if k in StockLevelDTO.__dataclass_fields__})

    async def get_reservation(self, order_id: str, user_id: str) -> ReservationDTO:
        data = await http.get(
            f"{_INVENTORY}/api/reservations/{order_id}/",
            headers=_user_headers(user_id),
        )
        return ReservationDTO(**{k: v for k, v in data.items() if k in ReservationDTO.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
# Shipping Service  (port 8005)
# ─────────────────────────────────────────────────────────────────────────────

_SHIPPING = config("SHIPPING_SERVICE_URL", default="http://shipping_service:8005")


class ShippingClient:

    async def get_shipment(self, order_id: str, user_id: str) -> ShipmentDTO:
        data = await http.get(
            f"{_SHIPPING}/api/shipments/{order_id}/",
            headers=_user_headers(user_id),
        )
        return shipment_dto_from_dict(data)

    async def get_shipments_batch(self, order_ids: list, user_id: str) -> list[ShipmentDTO]:
        """
        Batch fetch for ShipmentLoader.
        Expects: GET /api/shipments/?order_ids=id1,id2,id3
        """
        ids_param = ",".join(str(i) for i in order_ids)
        data = await http.get(
            f"{_SHIPPING}/api/shipments/",
            headers=_user_headers(user_id),
            params={"order_ids": ids_param},
        )
        return [shipment_dto_from_dict(s) for s in data.get("results", [])]


# ─────────────────────────────────────────────────────────────────────────────
# Notification Service  (port 8004)
# ─────────────────────────────────────────────────────────────────────────────

_NOTIFICATION = config("NOTIFICATION_SERVICE_URL", default="http://notification_service:8004")


class NotificationClient:

    async def list_notifications(
        self,
        user_id: str,
        order_id: str = None,
        channel: str = None,
        event_type: str = None,
    ) -> list[NotificationDTO]:
        params = {}
        if order_id:
            params["order_id"] = order_id
        if channel:
            params["channel"] = channel
        if event_type:
            params["event_type"] = event_type

        data = await http.get(
            f"{_NOTIFICATION}/api/notifications/",
            headers=_user_headers(user_id),
            params=params,
        )
        return [notification_dto_from_dict(n) for n in data.get("results", [])]


# ─────────────────────────────────────────────────────────────────────────────
# Singletons — import these in resolvers, not the classes directly
# ─────────────────────────────────────────────────────────────────────────────

account_client     = AccountClient()
order_client       = OrderClient()
payment_client     = PaymentClient()
inventory_client   = InventoryClient()
shipping_client    = ShippingClient()
notification_client = NotificationClient()
