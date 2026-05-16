from .models import Payment
from .dto.PaymentDto import PaymentObject, RefundObject

class PaymentBuilder:
    @staticmethod
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

    @staticmethod
    def _get_user_id(info) -> str:
        return info.context.META.get("HTTP_X_USER_ID")

