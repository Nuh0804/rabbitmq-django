import graphene
from django.utils import timezone
import uuid
from datetime import timedelta
from django.db import transaction
from .models import Product, StockLevel, StockReservation, StockReservationItem
from .builder import InventoryBuilder
from .dtos.ResponseDtos import ResponseObject
from .dtos.inventoryDtos import ProductWithStockObject, StockLevelObject, StockReservationObject, CreateProductInputObject, UpdateProductInputObject, AdjustStockInputObject, CreateReservationInputObject


class CreateProductMutation(graphene.Mutation):
    class Arguments:
        input = CreateProductInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(ProductWithStockObject)

    def mutate(cls, root, info, input):
        if not input.sku or not input.name:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if input.unit_price <= 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if input.initial_stock < 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if Product.objects.filter(sku=input.sku).exists():
            return cls(response=ResponseObject.get_response(id="12"), data=None)

        try:
            product = Product.objects.create(
                sku=input.sku,
                name=input.name,
                description=input.description or "",
                category=input.category or "",
                unit_price=input.unit_price,
                is_active=True,
            )
            StockLevel.objects.create(
                product=product,
                sku=input.sku,
                total=input.initial_stock,
                reserved=0,
                available=input.initial_stock,
            )
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=InventoryBuilder._product_to_object(product),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class UpdateProductMutation(graphene.Mutation):
    class Arguments:
        input = UpdateProductInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(ProductWithStockObject)

    def mutate(cls, root, info, input):
        try:
            product = Product.objects.select_related("stock").get(id=input.product_id)
        except Product.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        try:
            if input.name        is not None: product.name        = input.name
            if input.description is not None: product.description = input.description
            if input.category    is not None: product.category    = input.category
            if input.unit_price  is not None: product.unit_price  = input.unit_price
            if input.is_active   is not None: product.is_active   = input.is_active
            product.save()
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=InventoryBuilder._product_to_object(product),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class DeleteProductMutation(graphene.Mutation):
    """Soft delete — sets is_active=False."""
    class Arguments:
        product_id = graphene.UUID(required=True)

    response = graphene.Field(ResponseObject)

    def mutate(cls, root, info, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"))

        try:
            product.is_active = False
            product.save()
            return cls(response=ResponseObject.get_response(id="1"))
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"))


class AdjustStockMutation(graphene.Mutation):
    """
    Manual stock adjustment — add (positive) or remove (negative) units.
    Uses select_for_update() to prevent race conditions on concurrent adjustments.
    """
    class Arguments:
        input = AdjustStockInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(StockLevelObject)

    def mutate(cls, root, info, input):
        if input.quantity == 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            with transaction.atomic():
                stock = StockLevel.objects.select_for_update().get(sku=input.sku)

                new_total = stock.total + input.quantity
                if new_total < 0:
                    return cls(response=ResponseObject.get_response(id="13"), data=None)

                new_available = stock.available + input.quantity
                if new_available < 0:
                    return cls(response=ResponseObject.get_response(id="13"), data=None)

                stock.total     = new_total
                stock.available = new_available
                stock.save()

                return cls(
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
            return cls(response=ResponseObject.get_response(id="11"), data=None)
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class CreateReservationMutation(graphene.Mutation):
    """
    Reserve stock for an order.
    All items are reserved atomically — if any SKU has insufficient stock,
    the entire reservation is rolled back.
    """
    class Arguments:
        input = CreateReservationInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(StockReservationObject)

    def mutate(cls, root, info, input):
        if not input.items:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if StockReservation.objects.filter(order_id=input.order_id).exists():
            return cls(response=ResponseObject.get_response(id="12"), data=None)

        ttl_hours = input.ttl_hours or 24

        try:
            with transaction.atomic():
                # Lock all relevant stock rows upfront to prevent race conditions
                skus = [i.sku for i in input.items]
                stocks = {
                    s.sku: s
                    for s in StockLevel.objects.select_for_update().filter(sku__in=skus)
                }

                # Validate all SKUs exist and have enough stock
                for item in input.items:
                    stock = stocks.get(item.sku)
                    if not stock:
                        return cls(response=ResponseObject.get_response(id="11"), data=None)
                    if stock.available < item.quantity:
                        return cls(response=ResponseObject.get_response(id="13"), data=None)

                # Deduct available and add to reserved for each SKU
                for item in input.items:
                    stock = stocks[item.sku]
                    stock.available -= item.quantity
                    stock.reserved  += item.quantity
                    stock.save()

                reservation = StockReservation.objects.create(
                    order_id=input.order_id,
                    reservation_id=f"rsv_{uuid.uuid4().hex[:12]}",
                    status=StockReservation.Status.RESERVED,
                    expires_at=timezone.now() + timedelta(hours=ttl_hours),
                )
                for item in input.items:
                    StockReservationItem.objects.create(
                        reservation=reservation,
                        sku=item.sku,
                        quantity=item.quantity,
                    )

                return cls(
                    response=ResponseObject.get_response(id="1"),
                    data=InventoryBuilder._reservation_to_object(reservation),
                )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class ReleaseReservationMutation(graphene.Mutation):
    """
    Release a reservation and return stock to available.
    Called when an order is cancelled or payment fails.
    """
    class Arguments:
        order_id = graphene.UUID(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(StockReservationObject)

    def mutate(cls, root, info, order_id):
        try:
            reservation = StockReservation.objects.prefetch_related("items").get(
                order_id=order_id,
                status=StockReservation.Status.RESERVED,
            )
        except StockReservation.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        try:
            with transaction.atomic():
                skus = [i.sku for i in reservation.items.all()]
                stocks = {
                    s.sku: s
                    for s in StockLevel.objects.select_for_update().filter(sku__in=skus)
                }
                for item in reservation.items.all():
                    stock = stocks.get(item.sku)
                    if stock:
                        stock.available += item.quantity
                        stock.reserved  -= item.quantity
                        stock.save()

                reservation.status      = StockReservation.Status.RELEASED
                reservation.released_at = timezone.now()
                reservation.save()

                return cls(
                    response=ResponseObject.get_response(id="1"),
                    data=InventoryBuilder._reservation_to_object(reservation),
                )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class ConfirmDispatchMutation(graphene.Mutation):
    """
    Mark reservation as dispatched — stock is permanently deducted.
    Called when Shipping Service confirms the parcel has left the warehouse.
    """
    class Arguments:
        order_id = graphene.UUID(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(StockReservationObject)

    def mutate(cls, root, info, order_id):
        try:
            reservation = StockReservation.objects.prefetch_related("items").get(
                order_id=order_id,
                status=StockReservation.Status.RESERVED,
            )
        except StockReservation.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        try:
            with transaction.atomic():
                skus = [i.sku for i in reservation.items.all()]
                stocks = {
                    s.sku: s
                    for s in StockLevel.objects.select_for_update().filter(sku__in=skus)
                }
                for item in reservation.items.all():
                    stock = stocks.get(item.sku)
                    if stock:
                        # Move from reserved → permanently gone (reduce total)
                        stock.reserved -= item.quantity
                        stock.total -= item.quantity
                        stock.save()

                reservation.status = StockReservation.Status.DISPATCHED
                reservation.released_at = timezone.now()
                reservation.save()

                return cls(
                    response=ResponseObject.get_response(id="1"),
                    data=InventoryBuilder._reservation_to_object(reservation),
                )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class Mutation(graphene.ObjectType):
    create_product      = CreateProductMutation.Field()
    update_product      = UpdateProductMutation.Field()
    delete_product      = DeleteProductMutation.Field()
    adjust_stock        = AdjustStockMutation.Field()
    create_reservation  = CreateReservationMutation.Field()
    release_reservation = ReleaseReservationMutation.Field()
    confirm_dispatch    = ConfirmDispatchMutation.Field()