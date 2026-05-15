import graphene
from .models import Order, OrderItem, ShippingAddress
from .dtos.OrderDto import OrderObject, OrderItemObject, ShippingAddressObject

def _order_to_object(order: Order) -> OrderObject:
    items = [
        OrderItemObject(
            id=i.id,
            sku=i.sku,
            product_name=i.product_name,
            quantity=i.quantity,
            unit_price=i.unit_price,
            subtotal=i.subtotal,
        )
        for i in order.items.all()
    ]
    address = None
    if hasattr(order, "shipping_address"):
        a = order.shipping_address
        address = ShippingAddressObject(
            id=a.id,
            street=a.street,
            city=a.city,
            region=a.region,
            postal_code=a.postal_code,
            country=a.country,
            recipient_name=a.recipient_name,
            recipient_phone=a.recipient_phone,
        )
    return OrderObject(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        currency=order.currency,
        total_amount=order.total_amount,
        amount_charged=order.amount_charged,
        idempotency_key=order.idempotency_key,
        error_code=order.error_code,
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        shipping_address=address,
    )


def _get_user_id(info) -> str:
    """Extract user_id from request header set by the gateway."""
    return info.context.META.get("HTTP_X_USER_ID")

