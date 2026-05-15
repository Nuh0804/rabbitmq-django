"""
payment_service/graphene_schema.py
------------------------------------
Graphene ObjectTypes, InputObjects, Queries, and Mutations
for the Payment Service.

Wire into your project schema:
    # schema.py
    import graphene
    from .graphene_schema import Query, Mutation
    schema = graphene.Schema(query=Query, mutation=Mutation)

Wire into urls.py:
    from graphene_django.views import GraphQLView
    from django.views.decorators.csrf import csrf_exempt
    from .graphene_schema import schema
    path("graphql/", csrf_exempt(GraphQLView.as_view(schema=schema, graphiql=True)))

PAYMENT SIMULATOR INTEGRATION
-------------------------------
The simulator (simulators/payment_simulator.py) is called inside
ChargePaymentMutation.mutate(). Its return dict maps directly onto
the Payment model fields defined here.

Card number last digit controls simulator outcome:
    0, 5, 6, 8 → success
    1           → declined
    2           → insufficient_funds
    3, 4        → timeout  (RetryablePaymentError)
    7           → network_error  (RetryablePaymentError)
    9           → fraud_blocked
"""

import graphene
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Payment, Refund


# ─────────────────────────────────────────────────────────────────────────────
# Shared response / pagination objects
# ─────────────────────────────────────────────────────────────────────────────

RESPONSE_CODES = {
    "1":  {"message": "Success",                   "status": True},
    "5":  {"message": "Something went wrong",       "status": False},
    "8":  {"message": "Query error",                "status": False},
    "10": {"message": "Validation error",           "status": False},
    "11": {"message": "Not found",                  "status": False},
    "12": {"message": "Duplicate resource",         "status": False},
    "14": {"message": "Payment already processed",  "status": False},
    "15": {"message": "Refund not eligible",        "status": False},
}


class ResponseObject(graphene.ObjectType):
    message = graphene.String()
    status  = graphene.Boolean()

    @classmethod
    def get_response(cls, id: str):
        r = RESPONSE_CODES.get(str(id), RESPONSE_CODES["5"])
        return cls(message=r["message"], status=r["status"])


class PageObject(graphene.ObjectType):
    current_page = graphene.Int()
    total_pages  = graphene.Int()
    total_items  = graphene.Int()
    has_next     = graphene.Boolean()
    has_previous = graphene.Boolean()

    @classmethod
    def get_page(cls, page):
        return cls(
            current_page=page.number,
            total_pages=page.paginator.num_pages,
            total_items=page.paginator.count,
            has_next=page.has_next(),
            has_previous=page.has_previous(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# DTOs — ObjectTypes
# ─────────────────────────────────────────────────────────────────────────────

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
# Input objects
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _payment_to_object(payment: Payment) -> PaymentObject:
    refunds = [
        RefundObject(
            id=r.id,
            order_id=r.order_id,
            amount=r.amount,
            status=r.status,
            refund_id=r.refund_id,
            reason=r.reason,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in payment.refunds.all()
    ]
    return PaymentObject(
        id=payment.id,
        order_id=payment.order_id,
        user_id=payment.user_id,
        status=payment.status,
        currency=payment.currency,
        amount=payment.amount,
        amount_charged=payment.amount_charged,
        card_last_four=payment.card_last_four,
        payment_intent_id=payment.payment_intent_id,
        error_code=payment.error_code,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        refunds=refunds,
    )


def _get_user_id(info) -> str:
    return info.context.META.get("HTTP_X_USER_ID")


# ─────────────────────────────────────────────────────────────────────────────
# Mutations
# ─────────────────────────────────────────────────────────────────────────────

class ChargePaymentMutation(graphene.Mutation):
    """
    Charge a card for an order.

    Calls payment_simulator.charge_card() internally.
    The simulator outcome is determined by the last digit of card_number —
    see payment_simulator.py for the full card reference table.

    On RetryablePaymentError the consumer layer (not this mutation) is
    responsible for NACKing and requeueing the message. This mutation
    only handles the charge attempt and records the result.
    """
    class Arguments:
        input = ChargePaymentInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(PaymentObject)

    def mutate(cls, root, info, input):
        user_id = _get_user_id(info)
        if not user_id:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if input.amount <= 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if not input.currency:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        # One payment per order — reject duplicates
        if Payment.objects.filter(order_id=input.order_id).exclude(status=Payment.Status.PENDING).exists():
            return cls(response=ResponseObject.get_response(id="14"), data=None)

        from simulators.payment_simulator import (
            charge_card,
            RetryablePaymentError,
            NonRetryablePaymentError,
        )

        card_last_four = input.card_number[-4:] if len(input.card_number) >= 4 else "0000"

        # Create a pending payment record before calling the simulator
        payment = Payment.objects.create(
            order_id=input.order_id,
            user_id=user_id,
            status=Payment.Status.PENDING,
            currency=input.currency,
            amount=input.amount,
            card_last_four=card_last_four,
        )

        try:
            result = charge_card(
                card_number=input.card_number,
                amount=input.amount,
                currency=input.currency,
                order_id=str(input.order_id),
            )
        except RetryablePaymentError as e:
            # Do not update payment status — the consumer will retry
            # Raise so the consumer's NACK logic fires
            raise

        except NonRetryablePaymentError as e:
            payment.status     = Payment.Status.FAILED
            payment.error_code = "non_retryable_error"
            payment.save()
            return cls(
                response=ResponseObject.get_response(id="5"),
                data=_payment_to_object(payment),
            )

        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)

        if result["status"] == "success":
            payment.status            = Payment.Status.SUCCESS
            payment.amount_charged    = result["amount_charged"]
            payment.payment_intent_id = result["payment_intent_id"]
            payment.save()
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=_payment_to_object(payment),
            )

        # Non-retryable failure returned as result dict (declined, fraud, etc.)
        payment.status     = Payment.Status.FAILED
        payment.error_code = result.get("error_code")
        payment.save()
        return cls(
            response=ResponseObject.get_response(id="5"),
            data=_payment_to_object(payment),
        )


class RefundPaymentMutation(graphene.Mutation):
    """
    Refund a successfully charged payment.
    Only payments with status=success are eligible.
    """
    class Arguments:
        input = RefundPaymentInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(RefundObject)

    def mutate(cls, root, info, input):
        user_id = _get_user_id(info)
        if not user_id:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            payment = Payment.objects.get(order_id=input.order_id, user_id=user_id)
        except Payment.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        if payment.status != Payment.Status.SUCCESS:
            return cls(response=ResponseObject.get_response(id="15"), data=None)

        # Prevent duplicate refunds
        if payment.refunds.filter(status=Refund.Status.REFUNDED).exists():
            return cls(response=ResponseObject.get_response(id="12"), data=None)

        from simulators.payment_simulator import refund_payment

        try:
            result = refund_payment(
                payment_intent_id=payment.payment_intent_id,
                amount=payment.amount_charged,
            )
            refund = Refund.objects.create(
                payment=payment,
                order_id=payment.order_id,
                amount=payment.amount_charged,
                status=Refund.Status.REFUNDED,
                refund_id=result["refund_id"],
                reason=input.reason or "customer_request",
            )
            payment.status = Payment.Status.REFUNDED
            payment.save()

            return cls(
                response=ResponseObject.get_response(id="1"),
                data=RefundObject(
                    id=refund.id,
                    order_id=refund.order_id,
                    amount=refund.amount,
                    status=refund.status,
                    refund_id=refund.refund_id,
                    reason=refund.reason,
                    created_at=refund.created_at,
                    updated_at=refund.updated_at,
                ),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class UpdatePaymentStatusMutation(graphene.Mutation):
    """
    Internal mutation — called by consumer workers to update payment status.
    Not intended for direct client use.
    """
    class Arguments:
        order_id          = graphene.UUID(required=True)
        status            = graphene.String(required=True)
        error_code        = graphene.String()
        payment_intent_id = graphene.String()
        amount_charged    = graphene.Int()

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(PaymentObject)

    def mutate(cls, root, info, order_id, status, error_code=None,
               payment_intent_id=None, amount_charged=None):
        valid_statuses = [s.value for s in Payment.Status]
        if status not in valid_statuses:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            payment = Payment.objects.prefetch_related("refunds").get(order_id=order_id)
        except Payment.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        try:
            payment.status = status
            if error_code:
                payment.error_code = error_code
            if payment_intent_id:
                payment.payment_intent_id = payment_intent_id
            if amount_charged is not None:
                payment.amount_charged = amount_charged
            payment.save()
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=_payment_to_object(payment),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


# ─────────────────────────────────────────────────────────────────────────────
# Queries
# ─────────────────────────────────────────────────────────────────────────────

class Query(graphene.ObjectType):

    get_payment  = graphene.Field(
        PaymentResponseObject,
        order_id=graphene.UUID(required=True),
    )
    get_payments = graphene.Field(
        PaymentListResponseObject,
        filtering=PaymentFilteringInputObject(required=False),
    )

    def resolve_get_payment(self, info, order_id):
        user_id = _get_user_id(info)
        try:
            payment = Payment.objects.prefetch_related("refunds").get(
                order_id=order_id,
                user_id=user_id,
            )
            return PaymentResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=_payment_to_object(payment),
            )
        except Payment.DoesNotExist:
            return PaymentResponseObject(
                response=ResponseObject.get_response(id="11"),
                data=None,
            )
        except Exception as e:
            print(e)
            return PaymentResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_payments(self, info, filtering=None):
        """
        Supports single order_id, batch order_ids (for gateway DataLoader),
        and general filtering.
        """
        try:
            qs = Payment.objects.prefetch_related("refunds").all()

            if filtering:
                filters = Q()

                # Single order lookup
                if filtering.order_id:
                    filters &= Q(order_id=filtering.order_id)

                # Batch lookup — used by gateway PaymentLoader
                if filtering.order_ids:
                    filters &= Q(order_id__in=filtering.order_ids)

                if filtering.user_id:
                    filters &= Q(user_id=filtering.user_id)

                if filtering.status:
                    filters &= Q(status=filtering.status)

                if filtering.currency:
                    filters &= Q(currency=filtering.currency)

                if filters:
                    qs = qs.filter(filters)

            items_per_page = filtering.items_per_page if filtering and filtering.items_per_page else 10
            page_number    = filtering.page_number    if filtering and filtering.page_number    else 1

            paginated     = Paginator(qs, items_per_page)
            required_page = paginated.page(page_number)
            page_object   = PageObject.get_page(required_page)

            data = [_payment_to_object(p) for p in required_page]

            return PaymentListResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return PaymentListResponseObject(
                response=ResponseObject.get_response(id="8"),
                data=None,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Mutation registry
# ─────────────────────────────────────────────────────────────────────────────

class Mutation(graphene.ObjectType):
    charge_payment        = ChargePaymentMutation.Field()
    refund_payment        = RefundPaymentMutation.Field()
    update_payment_status = UpdatePaymentStatusMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
