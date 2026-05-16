"""
clients/service_clients.py  (updated for GraphQL services)
-----------------------------------------------------------
Each client method sends a GraphQL operation to its service's /graphql/
endpoint using base_client.gql().

WHAT CHANGED FROM THE REST VERSION
------------------------------------
- http.get/post/delete replaced with gql(service_url, query, variables)
- Response is response["data"]["fieldName"] instead of response directly
- GraphQL query strings defined inline as constants per method

WHAT STAYED THE SAME
---------------------
- DTO conversion (from_dto helpers in dtos.py) — unchanged
- Return types — unchanged
- Singleton instances at the bottom — unchanged
- How resolvers call these clients — unchanged

SERVICE GRAPHQL ENDPOINTS
--------------------------
Every service exposes exactly: POST /graphql/
Services accept X-User-ID header to identify the caller.
"""

from decouple import config
from .base_client import gql, DuplicateError
from ..dtos import (
    UserDTO, user_dto_from_dict,
    OrderDTO, CreateOrderResponseDTO, order_dto_from_dict,
    PaymentDTO, RefundResponseDTO, payment_dto_from_dict,
    StockLevelDTO, ReservationDTO,
    ShipmentDTO, shipment_dto_from_dict,
    NotificationDTO, notification_dto_from_dict,
    QueueStatsDTO, DLQMessageDTO,
)


_ACCOUNT      = config("ACCOUNT_SERVICE_URL",      default="http://account_service:8006")
_ORDER        = config("ORDER_SERVICE_URL",         default="http://order_service:8001")
_PAYMENT      = config("PAYMENT_SERVICE_URL",       default="http://payment_service:8002")
_INVENTORY    = config("INVENTORY_SERVICE_URL",     default="http://inventory_service:8003")
_SHIPPING     = config("SHIPPING_SERVICE_URL",      default="http://shipping_service:8005")
_NOTIFICATION = config("NOTIFICATION_SERVICE_URL",  default="http://notification_service:8004")


# ─────────────────────────────────────────────────────────────────────────────
# Account Service
# ─────────────────────────────────────────────────────────────────────────────

class AccountClient:

    async def get_me(self, user_id: str) -> UserDTO:
        data = await gql(
            _ACCOUNT,
            query="""
                query Me {
                    me {
                        id username email phone profilePic createdAt
                    }
                }
            """,
            user_id=user_id,
            operation_name="Me",
        )
        return user_dto_from_dict(data["me"])

    async def get_user(self, user_id: str, requester_id: str = None) -> UserDTO:
        data = await gql(
            _ACCOUNT,
            query="""
                query GetUser($id: ID!) {
                    user(id: $id) {
                        id username email phone profilePic createdAt
                    }
                }
            """,
            variables={"id": user_id},
            user_id=requester_id or user_id,
            operation_name="GetUser",
        )
        return user_dto_from_dict(data["user"])

    async def get_users_batch(self, user_ids: list, requester_id: str) -> list[UserDTO]:
        """
        Batch fetch for UserLoader.
        Service must support: query { users(ids: [...]) { ... } }
        """
        data = await gql(
            _ACCOUNT,
            query="""
                query GetUsersBatch($ids: [ID!]!) {
                    users(ids: $ids) {
                        id username email phone profilePic createdAt
                    }
                }
            """,
            variables={"ids": user_ids},
            user_id=requester_id,
            operation_name="GetUsersBatch",
        )
        return [user_dto_from_dict(u) for u in data.get("users", [])]

    async def update_profile(self, user_id: str, payload: dict) -> UserDTO:
        data = await gql(
            _ACCOUNT,
            query="""
                mutation UpdateProfile($input: UpdateProfileInput!) {
                    updateProfile(input: $input) {
                        id username email phone profilePic
                    }
                }
            """,
            variables={"input": payload},
            user_id=user_id,
            operation_name="UpdateProfile",
        )
        return user_dto_from_dict(data["updateProfile"])


# ─────────────────────────────────────────────────────────────────────────────
# Order Service
# ─────────────────────────────────────────────────────────────────────────────

class OrderClient:

    # GraphQL fragments reused across queries
    _ORDER_FIELDS = """
        fragment OrderFields on Order {
            id userId status currency totalAmount amountCharged
            errorCode errorMessage idempotencyKey createdAt updatedAt
            items { sku quantity unitPrice subtotal productName }
            shippingAddress {
                street city country region postalCode
                recipientName recipientPhone
            }
        }
    """

    async def get_order(self, order_id: str, user_id: str) -> OrderDTO:
        data = await gql(
            _ORDER,
            query=self._ORDER_FIELDS + """
                query GetOrder($id: ID!) {
                    order(id: $id) { ...OrderFields }
                }
            """,
            variables={"id": order_id},
            user_id=user_id,
            operation_name="GetOrder",
        )
        return order_dto_from_dict(data["order"])

    async def list_orders(self, user_id: str) -> list[OrderDTO]:
        data = await gql(
            _ORDER,
            query=self._ORDER_FIELDS + """
                query MyOrders {
                    myOrders { ...OrderFields }
                }
            """,
            user_id=user_id,
            operation_name="MyOrders",
        )
        return [order_dto_from_dict(o) for o in data.get("myOrders", [])]

    async def create_order(self, payload: dict, user_id: str) -> CreateOrderResponseDTO:
        try:
            data = await gql(
                _ORDER,
                query="""
                    mutation CreateOrder($input: CreateOrderInput!) {
                        createOrder(input: $input) {
                            id status totalAmount currency
                            duplicate idempotencyKey createdAt
                        }
                    }
                """,
                variables={"input": payload},
                user_id=user_id,
                operation_name="CreateOrder",
            )
            row = data["createOrder"]
            return CreateOrderResponseDTO(**{
                k: v for k, v in row.items()
                if k in CreateOrderResponseDTO.__dataclass_fields__
            })
        except DuplicateError as e:
            return CreateOrderResponseDTO(**{
                k: v for k, v in e.payload.items()
                if k in CreateOrderResponseDTO.__dataclass_fields__
            }, duplicate=True)

    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        await gql(
            _ORDER,
            query="""
                mutation CancelOrder($orderId: ID!) {
                    cancelOrder(orderId: $orderId) { success }
                }
            """,
            variables={"orderId": order_id},
            user_id=user_id,
            operation_name="CancelOrder",
        )
        return True

    async def get_debug_queues(self) -> list[QueueStatsDTO]:
        data = await gql(
            _ORDER,
            query="query { queueStats { name messages consumers durable } }",
            operation_name="QueueStats",
        )
        return [
            QueueStatsDTO(**{k: v for k, v in q.items() if k in QueueStatsDTO.__dataclass_fields__})
            for q in data.get("queueStats", [])
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Payment Service
# ─────────────────────────────────────────────────────────────────────────────

class PaymentClient:

    _PAYMENT_FIELDS = """
        fragment PaymentFields on Payment {
            id orderId status currency amountCharged
            paymentIntentId errorCode refundId refundedAmount createdAt
        }
    """

    async def get_payment(self, order_id: str, user_id: str) -> PaymentDTO:
        data = await gql(
            _PAYMENT,
            query=self._PAYMENT_FIELDS + """
                query GetPayment($orderId: ID!) {
                    payment(orderId: $orderId) { ...PaymentFields }
                }
            """,
            variables={"orderId": order_id},
            user_id=user_id,
            operation_name="GetPayment",
        )
        return payment_dto_from_dict(data["payment"])

    async def get_payments_batch(self, order_ids: list, user_id: str) -> list[PaymentDTO]:
        """Batch fetch for PaymentLoader — one call for N orders."""
        data = await gql(
            _PAYMENT,
            query=self._PAYMENT_FIELDS + """
                query GetPaymentsBatch($orderIds: [ID!]!) {
                    paymentsByOrders(orderIds: $orderIds) { ...PaymentFields }
                }
            """,
            variables={"orderIds": order_ids},
            user_id=user_id,
            operation_name="GetPaymentsBatch",
        )
        return [payment_dto_from_dict(p) for p in data.get("paymentsByOrders", [])]

    async def refund(self, order_id: str, user_id: str) -> RefundResponseDTO:
        data = await gql(
            _PAYMENT,
            query="""
                mutation RefundOrder($orderId: ID!) {
                    refundOrder(orderId: $orderId) {
                        refundId status amount orderId
                    }
                }
            """,
            variables={"orderId": order_id},
            user_id=user_id,
            operation_name="RefundOrder",
        )
        row = data["refundOrder"]
        return RefundResponseDTO(**{k: v for k, v in row.items() if k in RefundResponseDTO.__dataclass_fields__})

    async def get_dlq(self, queue_name: str) -> list[DLQMessageDTO]:
        data = await gql(
            _PAYMENT,
            query="""
                query DLQMessages($queueName: String!) {
                    dlqMessages(queueName: $queueName) {
                        orderId deathReason retryCount originalQueue firstDeathAt
                    }
                }
            """,
            variables={"queueName": queue_name},
            operation_name="DLQMessages",
        )
        return [
            DLQMessageDTO(**{k: v for k, v in m.items() if k in DLQMessageDTO.__dataclass_fields__})
            for m in data.get("dlqMessages", [])
        ]

    async def replay_dlq(self, queue_name: str, order_id: str) -> bool:
        await gql(
            _PAYMENT,
            query="""
                mutation ReplayDLQ($queueName: String!, $orderId: ID!) {
                    replayDlq(queueName: $queueName, orderId: $orderId) { success }
                }
            """,
            variables={"queueName": queue_name, "orderId": order_id},
            operation_name="ReplayDLQ",
        )
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Service
# ─────────────────────────────────────────────────────────────────────────────

class InventoryClient:

    async def get_stock_level(self, sku: str, user_id: str) -> StockLevelDTO:
        data = await gql(
            _INVENTORY,
            query="""
                query StockLevel($sku: String!) {
                    stockLevel(sku: $sku) {
                        sku available reserved total
                    }
                }
            """,
            variables={"sku": sku},
            user_id=user_id,
            operation_name="StockLevel",
        )
        return StockLevelDTO(**{k: v for k, v in data["stockLevel"].items() if k in StockLevelDTO.__dataclass_fields__})

    async def get_reservation(self, order_id: str, user_id: str) -> ReservationDTO:
        data = await gql(
            _INVENTORY,
            query="""
                query Reservation($orderId: ID!) {
                    reservation(orderId: $orderId) {
                        id orderId status reservationId reservedAt releasedAt
                    }
                }
            """,
            variables={"orderId": order_id},
            user_id=user_id,
            operation_name="Reservation",
        )
        return ReservationDTO(**{k: v for k, v in data["reservation"].items() if k in ReservationDTO.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────────────
# Shipping Service
# ─────────────────────────────────────────────────────────────────────────────

class ShippingClient:

    _SHIPMENT_FIELDS = """
        fragment ShipmentFields on Shipment {
            id orderId status trackingNumber carrier
            estimatedDeliveryDays dispatchedAt deliveredAt createdAt
            shippingAddress {
                street city country region postalCode
                recipientName recipientPhone
            }
        }
    """

    async def get_shipment(self, order_id: str, user_id: str) -> ShipmentDTO:
        data = await gql(
            _SHIPPING,
            query=self._SHIPMENT_FIELDS + """
                query GetShipment($orderId: ID!) {
                    shipment(orderId: $orderId) { ...ShipmentFields }
                }
            """,
            variables={"orderId": order_id},
            user_id=user_id,
            operation_name="GetShipment",
        )
        return shipment_dto_from_dict(data["shipment"])

    async def get_shipments_batch(self, order_ids: list, user_id: str) -> list[ShipmentDTO]:
        """Batch fetch for ShipmentLoader."""
        data = await gql(
            _SHIPPING,
            query=self._SHIPMENT_FIELDS + """
                query GetShipmentsBatch($orderIds: [ID!]!) {
                    shipmentsByOrders(orderIds: $orderIds) { ...ShipmentFields }
                }
            """,
            variables={"orderIds": order_ids},
            user_id=user_id,
            operation_name="GetShipmentsBatch",
        )
        return [shipment_dto_from_dict(s) for s in data.get("shipmentsByOrders", [])]


# ─────────────────────────────────────────────────────────────────────────────
# Notification Service
# ─────────────────────────────────────────────────────────────────────────────

class NotificationClient:

    async def list_notifications(
        self,
        user_id: str,
        order_id: str = None,
        channel: str = None,
        event_type: str = None,
    ) -> list[NotificationDTO]:
        data = await gql(
            _NOTIFICATION,
            query="""
                query Notifications($orderId: ID, $channel: String, $eventType: String) {
                    notifications(orderId: $orderId, channel: $channel, eventType: $eventType) {
                        id orderId channel eventType status recipient subject sentAt
                    }
                }
            """,
            variables={"orderId": order_id, "channel": channel, "eventType": event_type},
            user_id=user_id,
            operation_name="Notifications",
        )
        return [notification_dto_from_dict(n) for n in data.get("notifications", [])]


# ─────────────────────────────────────────────────────────────────────────────
# Singletons — import these in resolvers
# ─────────────────────────────────────────────────────────────────────────────

account_client      = AccountClient()
order_client        = OrderClient()
payment_client      = PaymentClient()
inventory_client    = InventoryClient()
shipping_client     = ShippingClient()
notification_client = NotificationClient()
