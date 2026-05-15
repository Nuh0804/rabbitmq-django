"""
inventory_service/seed.py
Run: python manage.py shell < seed.py
"""
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from inventory.models import Product, StockLevel, StockReservation, StockReservationItem

PRODUCTS = [
    dict(sku="SHOE-RED-42",       name="Red Running Shoes Size 42",  category="Footwear",    unit_price=75000),
    dict(sku="BAG-LEATHER-BLK",   name="Black Leather Bag",          category="Accessories", unit_price=45000),
    dict(sku="BOOK-KISWAHILI-01", name="Kiswahili Grammar Guide",    category="Books",       unit_price=25000),
    dict(sku="LAPTOP-CASE-14",    name="14-inch Laptop Case",        category="Electronics", unit_price=100000),
    dict(sku="SHIRT-WHITE-M",     name="White Cotton Shirt Medium",  category="Clothing",    unit_price=35000),
]

STOCK = [
    dict(sku="SHOE-RED-42",       total=50,  reserved=2,  available=48),
    dict(sku="BAG-LEATHER-BLK",   total=30,  reserved=1,  available=29),
    dict(sku="BOOK-KISWAHILI-01", total=100, reserved=0,  available=100),
    dict(sku="LAPTOP-CASE-14",    total=20,  reserved=0,  available=20),
    dict(sku="SHIRT-WHITE-M",     total=75,  reserved=0,  available=75),
]

# Reservations for orders that are PAID or SHIPPED
ORDER_IDS = [
    uuid.UUID("10000000-0000-0000-0000-000000000001"),
    uuid.UUID("10000000-0000-0000-0000-000000000002"),
]

def run():
    print("Seeding Inventory Service...")
    Product.objects.all().delete()
    StockLevel.objects.all().delete()
    StockReservation.objects.all().delete()

    products = {}
    for p, s in zip(PRODUCTS, STOCK):
        product = Product.objects.create(**p, is_active=True)
        StockLevel.objects.create(product=product, **s)
        products[p["sku"]] = product
        print(f"  ✓ Product {p['sku']} — stock: {s['available']} available")

    # Active reservation for order 1 (PAID — awaiting dispatch)
    res1 = StockReservation.objects.create(
        order_id=ORDER_IDS[0],
        reservation_id=f"sim_rsv_{uuid.uuid4().hex[:12]}",
        status=StockReservation.Status.RESERVED,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    StockReservationItem.objects.create(reservation=res1, sku="SHOE-RED-42", quantity=2)

    # Dispatched reservation for order 2 (SHIPPED)
    res2 = StockReservation.objects.create(
        order_id=ORDER_IDS[1],
        reservation_id=f"sim_rsv_{uuid.uuid4().hex[:12]}",
        status=StockReservation.Status.DISPATCHED,
        released_at=timezone.now(),
    )
    StockReservationItem.objects.create(reservation=res2, sku="BAG-LEATHER-BLK", quantity=1)

    print(f"Done. {Product.objects.count()} products, {StockReservation.objects.count()} reservations seeded.\n")

run()
