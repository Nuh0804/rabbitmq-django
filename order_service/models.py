
import uuid
from django.db import models


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING             = "pending"
        PAYMENT_PROCESSING  = "payment_processing"
        PAID                = "paid"
        FULFILLING          = "fulfilling"
        SHIPPED             = "shipped"
        DELIVERED           = "delivered"
        CANCELLED           = "cancelled"
        PAYMENT_FAILED      = "payment_failed"
        FULFILLMENT_FAILED  = "fulfillment_failed"

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id          = models.UUIDField(db_index=True)           # FK to Account Service
    status           = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    currency         = models.CharField(max_length=3, default="TZS")
    total_amount     = models.PositiveIntegerField(default=0)    # smallest currency unit
    amount_charged   = models.PositiveIntegerField(null=True, blank=True)
    idempotency_key  = models.CharField(max_length=255, unique=True, null=True, blank=True)
    error_code       = models.CharField(max_length=100, null=True, blank=True)
    error_message    = models.TextField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = "orders"
        ordering  = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} [{self.status}]"


class OrderItem(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    sku          = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    quantity     = models.PositiveIntegerField()
    unit_price   = models.PositiveIntegerField()   # smallest currency unit
    subtotal     = models.PositiveIntegerField()   # quantity * unit_price

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.sku} x{self.quantity}"


class ShippingAddress(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order          = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipping_address")
    street         = models.CharField(max_length=255)
    city           = models.CharField(max_length=100)
    region         = models.CharField(max_length=100, blank=True, null=True)
    postal_code    = models.CharField(max_length=20, blank=True, null=True)
    country        = models.CharField(max_length=2, default="TZ")
    recipient_name = models.CharField(max_length=100, blank=True, null=True)
    recipient_phone= models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "shipping_addresses"


class OutboxMessage(models.Model):
    """
    Transactional outbox — messages written here inside the same DB
    transaction as the business write, then published to RabbitMQ
    by a background worker. Guarantees no message is lost if the
    app crashes between DB write and broker publish.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type   = models.CharField(max_length=100)   # e.g. "order.created"
    payload      = models.JSONField()
    published    = models.BooleanField(default=False, db_index=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "outbox_messages"
        ordering = ["created_at"]


class IdempotencyKey(models.Model):
    """
    Tracks processed events to prevent duplicate processing.
    Pattern: before doing any work, check if (order_id, event_type) exists.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id   = models.UUIDField()
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "idempotency_keys"
        unique_together = [("order_id", "event_type")]
