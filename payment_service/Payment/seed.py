"""
payment_service/seed.py
Run: python manage.py shell < seed.py

NOTE: order_ids must match orders seeded in Order Service.
Replace with real UUIDs from your order_service DB.
"""
import uuid
from payments.models import Payment, Refund

ORDER_IDS = [
    uuid.UUID("10000000-0000-0000-0000-000000000001"),
    uuid.UUID("10000000-0000-0000-0000-000000000002"),
    uuid.UUID("10000000-0000-0000-0000-000000000003"),
    uuid.UUID("10000000-0000-0000-0000-000000000004"),
    uuid.UUID("10000000-0000-0000-0000-000000000005"),
]
USER_IDS = [
    uuid.UUID("00000000-0000-0000-0000-000000000001"),
    uuid.UUID("00000000-0000-0000-0000-000000000002"),
    uuid.UUID("00000000-0000-0000-0000-000000000003"),
    uuid.UUID("00000000-0000-0000-0000-000000000004"),
    uuid.UUID("00000000-0000-0000-0000-000000000005"),
]

PAYMENTS = [
    dict(order_id=ORDER_IDS[0], user_id=USER_IDS[0], currency="TZS", amount=150000,
         amount_charged=150000, card_last_four="0110", status=Payment.Status.SUCCESS,
         payment_intent_id="sim_pi_aabbcc001111"),
    dict(order_id=ORDER_IDS[1], user_id=USER_IDS[1], currency="TZS", amount=45000,
         amount_charged=45000,  card_last_four="0510", status=Payment.Status.SUCCESS,
         payment_intent_id="sim_pi_aabbcc002222"),
    dict(order_id=ORDER_IDS[2], user_id=USER_IDS[2], currency="TZS", amount=25000,
         amount_charged=None,   card_last_four="0010", status=Payment.Status.PENDING,
         payment_intent_id=None),
    dict(order_id=ORDER_IDS[3], user_id=USER_IDS[3], currency="TZS", amount=200000,
         amount_charged=None,   card_last_four="0110", status=Payment.Status.FAILED,
         payment_intent_id=None, error_code="declined"),
    dict(order_id=ORDER_IDS[4], user_id=USER_IDS[4], currency="TZS", amount=35000,
         amount_charged=35000,  card_last_four="0810", status=Payment.Status.REFUNDED,
         payment_intent_id="sim_pi_aabbcc005555"),
]

def run():
    print("Seeding Payment Service...")
    Payment.objects.all().delete()

    for p in PAYMENTS:
        payment = Payment.objects.create(**p)
        print(f"  ✓ Payment {payment.id} [{payment.status}] order={payment.order_id}")

        # Add a refund for the refunded payment
        if payment.status == Payment.Status.REFUNDED:
            Refund.objects.create(
                payment=payment,
                order_id=payment.order_id,
                amount=payment.amount_charged,
                status=Refund.Status.REFUNDED,
                refund_id=f"sim_re_{uuid.uuid4().hex[:12]}",
                reason="customer_request",
            )
            print(f"    ✓ Refund added for payment {payment.id}")

    print(f"Done. {Payment.objects.count()} payments seeded.\n")

run()
