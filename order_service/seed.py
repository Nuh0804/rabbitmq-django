"""
order_service/seed.py
Run: python manage.py shell < seed.py

NOTE: user_ids below must match UUIDs of users seeded in Account Service.
Replace them with real UUIDs from your Account Service DB, or leave as-is
for isolated testing — Order Service only stores user_id, never joins.
"""
import uuid
from orders.models import Order, OrderItem, ShippingAddress

# Use real UUIDs from your account_service DB, or generate placeholders
USER_IDS = [
    uuid.UUID("00000000-0000-0000-0000-000000000001"),
    uuid.UUID("00000000-0000-0000-0000-000000000002"),
    uuid.UUID("00000000-0000-0000-0000-000000000003"),
    uuid.UUID("00000000-0000-0000-0000-000000000004"),
    uuid.UUID("00000000-0000-0000-0000-000000000005"),
]

ORDERS = [
    dict(
        user_id=USER_IDS[0], currency="TZS", total_amount=150000,
        status=Order.Status.PAID,
        items=[
            dict(sku="SHOE-RED-42", product_name="Red Running Shoes", quantity=2, unit_price=75000, subtotal=150000),
        ],
        address=dict(street="Samora Avenue 12", city="Dar es Salaam", country="TZ", recipient_name="Nuh Admin"),
    ),
    dict(
        user_id=USER_IDS[1], currency="TZS", total_amount=45000,
        status=Order.Status.SHIPPED,
        items=[
            dict(sku="BAG-LEATHER-BLK", product_name="Black Leather Bag", quantity=1, unit_price=45000, subtotal=45000),
        ],
        address=dict(street="Kariakoo Market Rd", city="Dar es Salaam", country="TZ", recipient_name="Amina K"),
    ),
    dict(
        user_id=USER_IDS[2], currency="TZS", total_amount=25000,
        status=Order.Status.PENDING,
        items=[
            dict(sku="BOOK-KISWAHILI-01", product_name="Kiswahili Grammar", quantity=1, unit_price=25000, subtotal=25000),
        ],
        address=dict(street="Msasani Peninsula 4", city="Dar es Salaam", country="TZ", recipient_name="Juma Salim"),
    ),
    dict(
        user_id=USER_IDS[3], currency="TZS", total_amount=200000,
        status=Order.Status.PAYMENT_FAILED,
        items=[
            dict(sku="LAPTOP-CASE-14", product_name="14-inch Laptop Case", quantity=2, unit_price=100000, subtotal=200000),
        ],
        address=dict(street="Ubungo Msewe", city="Dar es Salaam", country="TZ", recipient_name="Fatuma Ali"),
    ),
    dict(
        user_id=USER_IDS[4], currency="TZS", total_amount=35000,
        status=Order.Status.DELIVERED,
        items=[
            dict(sku="SHIRT-WHITE-M", product_name="White Cotton Shirt M", quantity=1, unit_price=35000, subtotal=35000),
        ],
        address=dict(street="Sinza C Block 7", city="Dar es Salaam", country="TZ", recipient_name="David Peter"),
    ),
]

def run():
    print("Seeding Order Service...")
    Order.objects.all().delete()

    for o in ORDERS:
        order = Order.objects.create(
            user_id=o["user_id"],
            currency=o["currency"],
            total_amount=o["total_amount"],
            status=o["status"],
            idempotency_key=str(uuid.uuid4()),
        )
        for item in o["items"]:
            OrderItem.objects.create(order=order, **item)
        ShippingAddress.objects.create(order=order, **o["address"])
        print(f"  ✓ Order {order.id} [{order.status}] user={order.user_id}")

    print(f"Done. {Order.objects.count()} orders seeded.\n")

run()
