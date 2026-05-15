import graphene
from .dtos.inventoryDtos import *
from .dtos.ResponseDtos import ResponseObject, PageObject
from .models import Product, StockLevel, StockReservation
from .builder import InventoryBuilder
from django.db.models import Q
from django.core.paginator import Paginator

class Query(graphene.ObjectType):

    get_product      = graphene.Field(ProductResponseObject, sku=graphene.String(required=True))
    get_products     = graphene.Field(ProductListResponseObject, filtering=ProductFilteringInputObject(required=False))
    get_stock_level  = graphene.Field(StockLevelResponseObject, sku=graphene.String(required=True))
    get_reservation  = graphene.Field(ReservationResponseObject, order_id=graphene.UUID(required=True))
    get_reservations = graphene.Field(ReservationListResponseObject, filtering=ReservationFilteringInputObject(required=False))

    def resolve_get_product(self, info, sku):
        try:
            product = Product.objects.select_related("stock").get(sku=sku)
            return ProductResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=InventoryBuilder._product_to_object(product),
            )
        except Product.DoesNotExist:
            return ProductResponseObject(response=ResponseObject.get_response(id="11"), data=None)
        except Exception as e:
            print(e)
            return ProductResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_products(self, info, filtering=None):
        try:
            qs = Product.objects.select_related("stock").all()

            if filtering:
                filters = Q()
                if filtering.sku:
                    filters &= Q(sku__icontains=filtering.sku)
                if filtering.category:
                    filters &= Q(category=filtering.category)
                if filtering.is_active is not None:
                    filters &= Q(is_active=filtering.is_active)
                if filters:
                    qs = qs.filter(filters)

            items_per_page = filtering.items_per_page if filtering and filtering.items_per_page else 10
            page_number    = filtering.page_number    if filtering and filtering.page_number    else 1

            paginated     = Paginator(qs, items_per_page)
            required_page = paginated.page(page_number)
            page_object   = PageObject.get_page(required_page)

            data = [InventoryBuilder._product_to_object(p) for p in required_page]

            return ProductListResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return ProductListResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_stock_level(self, info, sku):
        try:
            stock = StockLevel.objects.get(sku=sku)
            return StockLevelResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=StockLevelObject(
                    id=stock.id,
                    sku=stock.sku,
                    total=stock.total,
                    reserved=stock.reserved,
                    available=stock.available,
                    updated_at=stock.updated_at,
                ),
            )
        except StockLevel.DoesNotExist:
            return StockLevelResponseObject(response=ResponseObject.get_response(id="11"), data=None)
        except Exception as e:
            print(e)
            return StockLevelResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_reservation(self, info, order_id):
        try:
            reservation = StockReservation.objects.prefetch_related("items").get(order_id=order_id)
            return ReservationResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=InventoryBuilder._reservation_to_object(reservation),
            )
        except StockReservation.DoesNotExist:
            return ReservationResponseObject(response=ResponseObject.get_response(id="11"), data=None)
        except Exception as e:
            print(e)
            return ReservationResponseObject(response=ResponseObject.get_response(id="8"), data=None)

    def resolve_get_reservations(self, info, filtering=None):
        try:
            qs = StockReservation.objects.prefetch_related("items").all()

            if filtering:
                filters = Q()
                if filtering.order_id:
                    filters &= Q(order_id=filtering.order_id)
                if filtering.status:
                    filters &= Q(status=filtering.status)
                if filters:
                    qs = qs.filter(filters)

            items_per_page = filtering.items_per_page if filtering and filtering.items_per_page else 10
            page_number    = filtering.page_number    if filtering and filtering.page_number    else 1

            paginated     = Paginator(qs, items_per_page)
            required_page = paginated.page(page_number)
            page_object   = PageObject.get_page(required_page)

            data = [InventoryBuilder._reservation_to_object(r) for r in required_page]

            return ReservationListResponseObject(
                response=ResponseObject.get_response(id="1"),
                data=data,
                page=page_object,
            )
        except Exception as e:
            print(e)
            return ReservationListResponseObject(response=ResponseObject.get_response(id="8"), data=None)
