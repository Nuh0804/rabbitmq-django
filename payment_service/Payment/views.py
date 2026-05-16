import graphene
from .builder import PaymentBuilder
from .dto.PaymentDto import (
    ChargePaymentInputObject,
    PaymentObject,
    RefundObject,
    RefundPaymentInputObject,
    ResponseObject,
)
from .models import Payment, Refund
from .payment_simulator import PaymentSimulator


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
        user_id = PaymentBuilder._get_user_id(info)
        if not user_id:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if input.amount <= 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if not input.currency:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        # One payment per order — reject duplicates
        if Payment.objects.filter(order_id=input.order_id).exclude(status=Payment.Status.PENDING).exists():
            return cls(response=ResponseObject.get_response(id="14"), data=None)

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
            result = PaymentSimulator.charge_card(
                card_number=input.card_number,
                amount=input.amount,
                currency=input.currency,
                order_id=str(input.order_id),
            )
        except PaymentSimulator.RetryablePaymentError as e:
            # Do not update payment status — the consumer will retry
            # Raise so the consumer's NACK logic fires
            raise

        except PaymentSimulator.NonRetryablePaymentError as e:
            payment.status     = Payment.Status.FAILED
            payment.error_code = "non_retryable_error"
            payment.save()
            return cls(
                response=ResponseObject.get_response(id="5"),
                data=PaymentBuilder._payment_to_object(payment),
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
                data=PaymentBuilder._payment_to_object(payment),
            )

        # Non-retryable failure returned as result dict (declined, fraud, etc.)
        payment.status     = Payment.Status.FAILED
        payment.error_code = result.get("error_code")
        payment.save()
        return cls(
            response=ResponseObject.get_response(id="5"),
            data=PaymentBuilder._payment_to_object(payment),
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
        user_id = PaymentBuilder._get_user_id(info)
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

        try:
            result = PaymentSimulator.refund_payment(
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
                data=PaymentBuilder._payment_to_object(payment),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class Mutation(graphene.ObjectType):
    charge_payment        = ChargePaymentMutation.Field()
    refund_payment        = RefundPaymentMutation.Field()
    update_payment_status = UpdatePaymentStatusMutation.Field()
