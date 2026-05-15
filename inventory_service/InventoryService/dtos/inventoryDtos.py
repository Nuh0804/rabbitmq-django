import graphene
from .ResponseDtos import ResponseObject, PageObject

class ProductObject(graphene.ObjectType):
    id          = graphene.UUID()
    sku         = graphene.String()
    name        = graphene.String()
    description = graphene.String()
    category    = graphene.String()
    unit_price  = graphene.Int()
    is_active   = graphene.Boolean()
    created_at  = graphene.DateTime()
    updated_at  = graphene.DateTime()


class StockLevelObject(graphene.ObjectType):
    id         = graphene.UUID()
    sku        = graphene.String()
    total      = graphene.Int()
    reserved   = graphene.Int()
    available  = graphene.Int()
    updated_at = graphene.DateTime()


class ProductWithStockObject(graphene.ObjectType):
    """Product and its current stock combined — the most common read shape."""
    id          = graphene.UUID()
    sku         = graphene.String()
    name        = graphene.String()
    description = graphene.String()
    category    = graphene.String()
    unit_price  = graphene.Int()
    is_active   = graphene.Boolean()
    created_at  = graphene.DateTime()
    stock       = graphene.Field(StockLevelObject)


class ReservationItemObject(graphene.ObjectType):
    id       = graphene.UUID()
    sku      = graphene.String()
    quantity = graphene.Int()


class StockReservationObject(graphene.ObjectType):
    id             = graphene.UUID()
    order_id       = graphene.UUID()
    reservation_id = graphene.String()
    status         = graphene.String()
    reserved_at    = graphene.DateTime()
    released_at    = graphene.DateTime()
    expires_at     = graphene.DateTime()
    items          = graphene.List(ReservationItemObject)


# ─────────────────────────────────────────────────────────────────────────────
# Response wrappers
# ─────────────────────────────────────────────────────────────────────────────

class ProductResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(ProductWithStockObject)


class ProductListResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.List(ProductWithStockObject)
    page     = graphene.Field(PageObject)


class StockLevelResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(StockLevelObject)


class ReservationResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(StockReservationObject)


class ReservationListResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.List(StockReservationObject)
    page     = graphene.Field(PageObject)


# ─────────────────────────────────────────────────────────────────────────────
# Input objects
# ─────────────────────────────────────────────────────────────────────────────

class CreateProductInputObject(graphene.InputObjectType):
    sku         = graphene.String(required=True)
    name        = graphene.String(required=True)
    description = graphene.String()
    category    = graphene.String()
    unit_price  = graphene.Int(required=True)
    initial_stock = graphene.Int(required=True)


class UpdateProductInputObject(graphene.InputObjectType):
    product_id  = graphene.UUID(required=True)
    name        = graphene.String()
    description = graphene.String()
    category    = graphene.String()
    unit_price  = graphene.Int()
    is_active   = graphene.Boolean()


class AdjustStockInputObject(graphene.InputObjectType):
    """
    Add or remove stock manually.
    Use positive quantity to add, negative to remove.
    """
    sku      = graphene.String(required=True)
    quantity = graphene.Int(required=True)
    reason   = graphene.String()


class ReservationItemInputObject(graphene.InputObjectType):
    sku      = graphene.String(required=True)
    quantity = graphene.Int(required=True)


class CreateReservationInputObject(graphene.InputObjectType):
    order_id      = graphene.UUID(required=True)
    items         = graphene.List(graphene.NonNull(ReservationItemInputObject), required=True)
    ttl_hours     = graphene.Int()   # reservation expiry in hours, default 24


class ProductFilteringInputObject(graphene.InputObjectType):
    sku            = graphene.String()
    category       = graphene.String()
    is_active      = graphene.Boolean()
    items_per_page = graphene.Int()
    page_number    = graphene.Int()


class ReservationFilteringInputObject(graphene.InputObjectType):
    order_id       = graphene.UUID()
    status         = graphene.String()
    items_per_page = graphene.Int()
    page_number    = graphene.Int()

