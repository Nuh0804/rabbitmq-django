"""
inventory_service/models.py
"""
import uuid
from django.db import models


class Product(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku         = models.CharField(max_length=100, unique=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category    = models.CharField(max_length=100, blank=True, null=True)
    unit_price  = models.PositiveIntegerField(default=0)   # canonical price in TZS
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return f"{self.sku} — {self.name}"


class StockLevel(models.Model):
    """
    Current stock for a product.
    available + reserved = total.
    Write operations use select_for_update() to prevent race conditions.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product     = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stock")
    sku         = models.CharField(max_length=100, unique=True)  # denormalised for fast lookup
    total       = models.PositiveIntegerField(default=0)
    reserved    = models.PositiveIntegerField(default=0)
    available   = models.PositiveIntegerField(default=0)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_levels"

    def __str__(self):
        return f"{self.sku}: available={self.available} reserved={self.reserved}"


class StockReservation(models.Model):

    class Status(models.TextChoices):
        RESERVED   = "reserved"
        RELEASED   = "released"
        DISPATCHED = "dispatched"
        EXPIRED    = "expired"

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id       = models.UUIDField(unique=True, db_index=True)
    reservation_id = models.CharField(max_length=100, unique=True)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    reserved_at    = models.DateTimeField(auto_now_add=True)
    released_at    = models.DateTimeField(null=True, blank=True)
    expires_at     = models.DateTimeField(null=True, blank=True)  # TTL-based release

    class Meta:
        db_table = "stock_reservations"


class StockReservationItem(models.Model):
    """Line items within a reservation — one row per SKU per order."""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(StockReservation, on_delete=models.CASCADE, related_name="items")
    sku         = models.CharField(max_length=100)
    quantity    = models.PositiveIntegerField()

    class Meta:
        db_table = "stock_reservation_items"


class IdempotencyKey(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id     = models.UUIDField()
    event_type   = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "idempotency_keys"
        unique_together = [("order_id", "event_type")]


class OutboxMessage(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type   = models.CharField(max_length=100)
    payload      = models.JSONField()
    published    = models.BooleanField(default=False, db_index=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "outbox_messages"
        ordering = ["created_at"]
