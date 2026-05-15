import graphene
from .models import Product, StockLevel, StockReservation, StockReservationItem
from .dtos.inventoryDtos import ProductWithStockObject, StockLevelObject, StockReservationObject, ReservationItemObject
def _product_to_object(product: Product) -> ProductWithStockObject:
    stock = None
    if hasattr(product, "stock"):
        s = product.stock
        stock = StockLevelObject(
            id=s.id,
            sku=s.sku,
            total=s.total,
            reserved=s.reserved,
            available=s.available,
            updated_at=s.updated_at,
        )
    return ProductWithStockObject(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category=product.category,
        unit_price=product.unit_price,
        is_active=product.is_active,
        created_at=product.created_at,
        stock=stock,
    )


def _reservation_to_object(reservation: StockReservation) -> StockReservationObject:
    items = [
        ReservationItemObject(id=i.id, sku=i.sku, quantity=i.quantity)
        for i in reservation.items.all()
    ]
    return StockReservationObject(
        id=reservation.id,
        order_id=reservation.order_id,
        reservation_id=reservation.reservation_id,
        status=reservation.status,
        reserved_at=reservation.reserved_at,
        released_at=reservation.released_at,
        expires_at=reservation.expires_at,
        items=items,
    )


def _get_user_id(info) -> str:
    return info.context.META.get("HTTP_X_USER_ID")