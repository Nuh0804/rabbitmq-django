import graphene
from .models import Order
from .builder import OrderBuilder
from .dtos.ResponseDtos import ResponseObject, PageObject
from .dtos.OrderDto import OrderResponseObject, OrderListResponseObject, OrderFilteringInputObject
from django.db.models import Q
from django.core.paginator import Paginator

class Query(graphene.ObjectType):

    get_order  = graphene.Field(OrderResponseObject, order_id=graphene.UUID(required=True),)
    get_orders = graphene.Field(OrderListResponseObject, filtering=OrderFilteringInputObject(required=False))
    get_my_orders = graphene.Field(OrderListResponseObject, filtering=OrderFilteringInputObject(required=False))

    def resolve_get_order(self, info, order_id):
        user_id = OrderBuilder._get_user_id(info)
        try:
            order = Order.objects.prefetch_related("items").select_related("shipping_address").get(
                id=order_id,
                user_id=user_id,
            )
            return OrderResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=OrderBuilder._order_to_object(order),
            )
        except Order.DoesNotExist:
            return OrderResponseObject(
                response=ResponseObject.get_response(id="11"),
                data=None,
            )
        except Exception as e:
            print(e)
            return OrderResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_orders(self, info, filtering=None):
        """All orders — intended for admin/internal use."""
        try:
            qs = Order.objects.prefetch_related("items").select_related("shipping_address").all()

            if filtering:
                filters = Q()
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

            data = [OrderBuilder._order_to_object(o) for o in required_page]

            return OrderListResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return OrderListResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_my_orders(self, info, filtering=None):
        """Orders belonging to the authenticated user."""
        user_id = OrderBuilder._get_user_id(info)
        if not user_id:
            return OrderListResponseObject(
                response=ResponseObject.get_response(id="10"),
                data=None,
            )
        try:
            qs = Order.objects.prefetch_related("items").select_related("shipping_address").filter(
                user_id=user_id
            )

            if filtering:
                filters = Q()
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

            data = [OrderBuilder._order_to_object(o) for o in required_page]

            return OrderListResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return OrderListResponseObject(response=ResponseObject.get_response(id="8"), data=None)

