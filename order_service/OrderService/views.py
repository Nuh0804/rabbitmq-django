import graphene
from .models import Order, OrderItem, ShippingAddress
from .dtos.OrderDto import OrderObject, OrderItemObject, ShippingAddressObject
from .builder import OrderBuilder
from django.db import transaction
from .dtos.ResponseDtos import ResponseObject
from .dtos.OrderDto import CreateOrderInputObject, UpdateOrderStatusInputObject
from .externalService import ExternalServices
from .exceptions import ReservationFailedError

class CreateOrderMutation(graphene.Mutation):
    class Arguments:
        input = CreateOrderInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(OrderObject)

    @classmethod
    def mutate(cls, root, info, input):
        user_id = OrderBuilder._get_user_id(info) or "9b8acafb-4287-4c52-8244-89ecd45fcf33"
        if not user_id:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if not input.items:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        # Validate all items have positive quantity and price
        for item in input.items:
            if item.quantity <= 0 or item.unit_price <= 0:
                return cls(response=ResponseObject.get_response(id="10"), data=None)

        total_amount = sum(i.quantity * i.unit_price for i in input.items)
        if total_amount <= 0:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user_id=user_id,
                    currency=input.currency,
                    total_amount=total_amount,
                    status=Order.Status.PENDING,
                    idempotency_key=input.idempotency_key or None,
                )

                #prepare data to send to inventory service            
                inventory_payload = {
                    "orderId" : str(order.id),
                    "items" : [
                        {"sku": item.sku, "quantity": item.quantity} for item in input.items
                    ]
                }
                print(f"the inventory items are {inventory_payload}")

                success, id = ExternalServices.create_reservation(inventory_payload)
                print(f"{success} for {id}")
                if success == False:
                    raise ReservationFailedError(id)
                
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order = order, 
                        sku = item.sku,
                        product_name = item.product_name or "",
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.quantity * item.unit_price,
                    )
                    for item in input.items
                ])
                addr = input.shipping_address
                ShippingAddress.objects.create(
                    order=order,
                    street=addr.street,
                    city=addr.city,
                    country=addr.country,
                    region=addr.region or "",
                    postal_code=addr.postal_code or "",
                    recipient_name=addr.recipient_name or "",
                    recipient_phone=addr.recipient_phone or "",
                )

            return cls(
                response=ResponseObject.get_response(id="1"),
                data=OrderBuilder._order_to_object(order),
            )
        except ReservationFailedError as e:
            # transaction.atomic() already rolled back the order row
            print(e)
            return cls(response=ResponseObject.get_response(id=e.code), data=None)
        
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="8"), data=None)


class UpdateOrderStatusMutation(graphene.Mutation):
    """
    Called internally by consumer workers to advance order state.
    e.g. payment.succeeded → set status=paid
    """
    class Arguments:
        input = UpdateOrderStatusInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data     = graphene.Field(OrderObject)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            order = Order.objects.get(id=input.order_id)
        except Order.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        valid_statuses = [s.value for s in Order.Status]
        if input.status not in valid_statuses:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            order.status = input.status
            if input.error_code:
                order.error_code = input.error_code
            if input.error_message:
                order.error_message = input.error_message
            order.save()
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=OrderBuilder._order_to_object(order),
            )
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class CancelOrderMutation(graphene.Mutation):
    class Arguments:
        order_id = graphene.UUID(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(OrderObject)

    @classmethod
    def mutate(cls, root, info, order_id):
        user_id = OrderBuilder._get_user_id(info) or "9b8acafb-4287-4c52-8244-89ecd45fcf33"
        try:
            order = Order.objects.get(id=order_id, user_id=user_id)
        except Order.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"), data=None)

        cancellable = [
            Order.Status.PENDING,
            Order.Status.PAYMENT_PROCESSING,
        ]
        if order.status not in cancellable:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        try:
            with transaction.atomic():
                order.status = Order.Status.CANCELLED
                order.save()
                success, id = ExternalServices.release_reservation(str(order.id))
                if not success:
                    raise  ReservationFailedError(id)
            return cls(
                response=ResponseObject.get_response(id="1"),
                data=OrderBuilder._order_to_object(order),
            )
        except ReservationFailedError as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)


class DeleteOrderMutation(graphene.Mutation):
    """Hard delete — only for cancelled or failed orders."""
    class Arguments:
        order_id = graphene.UUID(required=True)

    response = graphene.Field(ResponseObject)

    @classmethod
    def mutate(cls, root, info, order_id):
        user_id = OrderBuilder._get_user_id(info)
        try:
            order = Order.objects.get(id=order_id, user_id=user_id)
        except Order.DoesNotExist:
            return cls(response=ResponseObject.get_response(id="11"))

        deletable = [Order.Status.CANCELLED, Order.Status.PAYMENT_FAILED]
        if order.status not in deletable:
            return cls(response=ResponseObject.get_response(id="10"))

        try:
            order.delete()
            return cls(response=ResponseObject.get_response(id="1"))
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"))



class Mutation(graphene.ObjectType):
    create_order        = CreateOrderMutation.Field()
    update_order_status = UpdateOrderStatusMutation.Field()
    cancel_order        = CancelOrderMutation.Field()
    delete_order        = DeleteOrderMutation.Field()

