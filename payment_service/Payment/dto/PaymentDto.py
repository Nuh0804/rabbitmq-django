import graphene
from .ResponseDtos import ResponseObject, PageObject

class RefundObject(graphene.ObjectType):
    id         = graphene.UUID()
    order_id   = graphene.UUID()
    amount     = graphene.Int()
    status     = graphene.String()
    refund_id  = graphene.String()
    reason     = graphene.String()
    created_at = graphene.DateTime()
    updated_at = graphene.DateTime()


class PaymentObject(graphene.ObjectType):
    id                = graphene.UUID()
    order_id          = graphene.UUID()
    user_id           = graphene.UUID()
    status            = graphene.String()   # pending | success | failed | refunded
    currency          = graphene.String()
    amount            = graphene.Int()      # intended charge amount
    amount_charged    = graphene.Int()      # actual charged (None if not yet charged)
    card_last_four    = graphene.String()
    payment_intent_id = graphene.String()
    error_code        = graphene.String()
    created_at        = graphene.DateTime()
    updated_at        = graphene.DateTime()
    refunds           = graphene.List(RefundObject)


# ─────────────────────────────────────────────────────────────────────────────
# Response wrappers
# ─────────────────────────────────────────────────────────────────────────────

class PaymentResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(PaymentObject)


class PaymentListResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.List(PaymentObject)
    page     = graphene.Field(PageObject)


class RefundResponseObject(graphene.ObjectType):
    response = graphene.Field(ResponseObject)
    data     = graphene.Field(RefundObject)


# ─────────────────────────────────────────────────────────────────────────────
# Input objectss
# ─────────────────────────────────────────────────────────────────────────────

class ChargePaymentInputObject(graphene.InputObjectType):
    order_id    = graphene.UUID(required=True)
    amount      = graphene.Int(required=True)
    currency    = graphene.String(required=True)
    card_number = graphene.String(required=True)


class RefundPaymentInputObject(graphene.InputObjectType):
    order_id = graphene.UUID(required=True)
    reason   = graphene.String()


class PaymentFilteringInputObject(graphene.InputObjectType):
    order_id       = graphene.UUID()
    order_ids      = graphene.List(graphene.UUID)   # batch fetch for gateway DataLoader
    user_id        = graphene.UUID()
    status         = graphene.String()
    currency       = graphene.String()
    items_per_page = graphene.Int()
    page_number    = graphene.Int()

