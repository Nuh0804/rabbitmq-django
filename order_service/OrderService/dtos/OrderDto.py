import graphene
from .ResponseDtos import ResponseObject, PageObject

class ShippingAddressObject(graphene.ObjectType):
    id             = graphene.UUID()
    street         = graphene.String()
    city           = graphene.String()
    region         = graphene.String()
    postal_code    = graphene.String()
    country        = graphene.String()
    recipient_name = graphene.String()
    recipient_phone= graphene.String()


class OrderItemObject(graphene.ObjectType):
    id           = graphene.UUID()
    sku          = graphene.String()
    product_name = graphene.String()
    quantity     = graphene.Int()
    unit_price   = graphene.Int()
    subtotal     = graphene.Int()


class OrderObject(graphene.ObjectType):
    id               = graphene.UUID()
    user_id          = graphene.UUID()
    status           = graphene.String()
    currency         = graphene.String()
    total_amount     = graphene.Int()
    amount_charged   = graphene.Int()
    idempotency_key  = graphene.String()
    error_code       = graphene.String()
    error_message    = graphene.String()
    created_at       = graphene.DateTime()
    updated_at       = graphene.DateTime()
    items            = graphene.List(OrderItemObject)
    shipping_address = graphene.Field(ShippingAddressObject)


# ─────────────────────────────────────────────────────────────────────────────
# Response wrappers
# ─────────────────────────────────────────────────────────────────────────────

class OrderResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(OrderObject)


class OrderListResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.List(OrderObject)
    page     = graphene.Field(PageObject)


# ─────────────────────────────────────────────────────────────────────────────
# Input objects
# ─────────────────────────────────────────────────────────────────────────────

class ShippingAddressInputObject(graphene.InputObjectType):
    street          = graphene.String(required=True)
    city            = graphene.String(required=True)
    country         = graphene.String(required=True)
    region          = graphene.String()
    postal_code     = graphene.String()
    recipient_name  = graphene.String()
    recipient_phone = graphene.String()


class OrderItemInputObject(graphene.InputObjectType):
    sku          = graphene.String(required=True)
    quantity     = graphene.Int(required=True)
    unit_price   = graphene.Int(required=True)
    product_name = graphene.String()


class CreateOrderInputObject(graphene.InputObjectType):
    currency         = graphene.String(required=True)
    card_number      = graphene.String(required=True)
    items            = graphene.List(graphene.NonNull(OrderItemInputObject), required=True)
    shipping_address = graphene.Argument(ShippingAddressInputObject, required=True)
    idempotency_key  = graphene.String()


class UpdateOrderStatusInputObject(graphene.InputObjectType):
    order_id      = graphene.UUID(required=True)
    status        = graphene.String(required=True)
    error_code    = graphene.String()
    error_message = graphene.String()


class OrderFilteringInputObject(graphene.InputObjectType):
    user_id        = graphene.UUID()
    status         = graphene.String()
    currency       = graphene.String()
    items_per_page = graphene.Int()
    page_number    = graphene.Int()

