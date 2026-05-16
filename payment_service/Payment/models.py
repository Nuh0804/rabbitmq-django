"""
payment_service/models.py
"""
import uuid
from django.db import models


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING  = "pending"
        SUCCESS  = "success"
        FAILED   = "failed"
        REFUNDED = "refunded"

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id           = models.UUIDField(unique=True, db_index=True)   # FK to Order Service
    user_id            = models.UUIDField(db_index=True)
    status             = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    currency           = models.CharField(max_length=3, default="TZS")
    amount             = models.PositiveIntegerField()          # intended charge amount
    amount_charged     = models.PositiveIntegerField(null=True, blank=True)  # actual charged
    card_last_four     = models.CharField(max_length=4, blank=True, null=True)
    payment_intent_id  = models.CharField(max_length=100, null=True, blank=True, unique=True)
    error_code         = models.CharField(max_length=100, null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment {self.id} [{self.status}] order={self.order_id}"


class Refund(models.Model):

    class Status(models.TextChoices):
        PENDING  = "pending"
        REFUNDED = "refunded"
        FAILED   = "failed"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment     = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    order_id    = models.UUIDField(db_index=True)
    amount      = models.PositiveIntegerField()
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    refund_id   = models.CharField(max_length=100, null=True, blank=True)  # from payment gateway
    reason      = models.CharField(max_length=100, default="customer_request")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "refunds"


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
