import graphene
from .dto.PaymentDto import PaymentResponseObject, PaymentListResponseObject, PaymentFilteringInputObject
from .models import Payment
from .builder import PaymentBuilder
from .dto.ResponseDtos import ResponseObject, PageObject
from django.db.models import Q
from django.core.paginator import Paginator

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
        user_id = PaymentBuilder._get_user_id(info)
        try:
            payment = Payment.objects.prefetch_related("refunds").get(
                order_id=order_id,
                user_id=user_id,
            )
            return PaymentResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=PaymentBuilder._payment_to_object(payment),
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

            data = [PaymentBuilder._payment_to_object(p) for p in required_page]

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

