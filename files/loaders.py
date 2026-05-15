"""
dataloaders/loaders.py
-----------------------
DataLoaders batch multiple individual HTTP calls into one.

THE N+1 PROBLEM THIS SOLVES
-----------------------------
Without DataLoader:
    Query asks for 10 orders → resolve_payment runs 10 times
    → 10 separate GET /payments/?order_id=X calls

With DataLoader:
    Query asks for 10 orders → each resolve_payment calls loader.load(order_id)
    → loader waits for all 10 resolvers in this execution tick to register
    → ONE call: GET /payments/?order_ids=id1,id2,...,id10
    → results fanned back to each resolver automatically

KEY RULE: DataLoaders MUST be instantiated fresh per request.
They are created in context.py, not here. This file only
defines the loader classes.

If you instantiate them as module-level singletons, their internal
batch queue persists across requests and you get cross-user data leaks.
"""

from promise import Promise
from promise.dataloader import DataLoader


class PaymentLoader(DataLoader):
    """
    Batches payment fetches across all orders in a single GraphQL request.

    Used in: OrderType.resolve_payment
    Calls:   PaymentClient.get_payments_batch(order_ids)
    """

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id

    def batch_load_fn(self, order_ids: list):
        return Promise.resolve(self._fetch(order_ids))

    async def _fetch(self, order_ids: list):
        from ..clients.service_clients import payment_client
        payments = await payment_client.get_payments_batch(order_ids, self.user_id)

        # Index by order_id so we can return results in the same order
        # as order_ids (DataLoader contract requires this)
        index = {p.order_id: p for p in payments}

        # Return None for any order_id that has no payment yet
        return [index.get(oid) for oid in order_ids]


class ShipmentLoader(DataLoader):
    """
    Batches shipment fetches across all orders in a single GraphQL request.

    Used in: OrderType.resolve_shipment
    Calls:   ShippingClient.get_shipments_batch(order_ids)
    """

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id

    def batch_load_fn(self, order_ids: list):
        return Promise.resolve(self._fetch(order_ids))

    async def _fetch(self, order_ids: list):
        from ..clients.service_clients import shipping_client
        shipments = await shipping_client.get_shipments_batch(order_ids, self.user_id)
        index = {s.order_id: s for s in shipments}
        return [index.get(oid) for oid in order_ids]


class UserLoader(DataLoader):
    """
    Batches user profile fetches.
    Useful if a query returns many orders that each need the owner's profile.

    Used in: any type that has a user_id field and needs UserType
    Calls:   AccountClient.get_users_batch(user_ids)
    """

    def __init__(self, requester_id: str):
        super().__init__()
        self.requester_id = requester_id

    def batch_load_fn(self, user_ids: list):
        return Promise.resolve(self._fetch(user_ids))

    async def _fetch(self, user_ids: list):
        from files.service_clients import account_client
        users = await account_client.get_users_batch(user_ids, self.requester_id)
        index = {u.id: u for u in users}
        return [index.get(uid) for uid in user_ids]
