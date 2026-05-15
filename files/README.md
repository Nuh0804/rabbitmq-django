# API Gateway

Django + Graphene GraphQL gateway for the e-commerce microservices project.

---

## File structure

```
gateway/                        ← Django app (create with: django-admin startapp gateway)
├── dtos.py                     ← Data Transfer Objects — mirrors service JSON responses
├── types.py                    ← Graphene ObjectTypes — what the GraphQL client sees
├── queries.py                  ← All Query resolvers
├── mutations.py                ← All Mutation resolvers
├── schema.py                   ← Wires Query + Mutation → graphene.Schema
├── context.py                  ← Per-request context (user_id + DataLoaders)
├── auth.py                     ← JWT verification
├── urls.py                     ← Single /graphql/ endpoint
├── settings_additions.py       ← Settings to add to settings.py (non-defaults only)
├── clients/
│   ├── __init__.py
│   ├── base_client.py          ← Shared httpx session + error handling
│   └── service_clients.py      ← One client class per downstream service
└── dataloaders/
    ├── __init__.py
    └── loaders.py              ← PaymentLoader, ShipmentLoader, UserLoader
```

---

## How to stitch into your Django project

### 1. Create the Django project and app

```bash
django-admin startproject api_gateway .
python manage.py startapp gateway
```

### 2. Copy these files into the gateway/ app directory

Place each file at the path shown in the structure above.

### 3. Update settings.py

Open `settings_additions.py` and copy each section into `settings.py`.
The key additions are:
- Add `"graphene_django"` and `"gateway"` to `INSTALLED_APPS`
- Add the `GRAPHENE` dict
- Add logging config
- Set `ASGI_APPLICATION`

### 4. Update project urls.py

```python
from django.urls import path, include

urlpatterns = [
    path("", include("gateway.urls")),
]
```

### 5. Create .env

```
ACCOUNT_SERVICE_URL=http://localhost:8006
ORDER_SERVICE_URL=http://localhost:8001
PAYMENT_SERVICE_URL=http://localhost:8002
INVENTORY_SERVICE_URL=http://localhost:8003
SHIPPING_SERVICE_URL=http://localhost:8005
NOTIFICATION_SERVICE_URL=http://localhost:8004
JWT_SECRET=your-secret-here
JWT_ALGORITHM=HS256
SERVICE_TIMEOUT_SECONDS=10
DEBUG=True
```

### 6. Install dependencies

```bash
pip install -r requirements.txt
```

### 7. Run the gateway

```bash
python manage.py runserver 8000
```

GraphiQL playground: http://localhost:8000/graphql/

---

## Getting a test JWT token

```bash
python manage.py shell
>>> from gateway.auth import create_test_token
>>> print(create_test_token("user-001"))
```

Use the token in GraphiQL or Postman:
```
Authorization: Bearer <token>
```

---

## Sample GraphQL queries to test in GraphiQL

### Get your profile + orders + payment status (cross-service query)
```graphql
query Me {
  me {
    id
    username
    email
    orders {
      id
      status
      totalAmount
      payment {
        status
        amountCharged
      }
      shipment {
        trackingNumber
        carrier
        status
      }
    }
  }
}
```

### Place an order
```graphql
mutation PlaceOrder {
  createOrder(input: {
    currency: "TZS"
    cardNumber: "4111111111110"
    idempotencyKey: "my-unique-key-001"
    items: [{ sku: "SHOE-RED-42", quantity: 2, unitPrice: 75000 }]
    shippingAddress: {
      street: "Samora Avenue 12"
      city: "Dar es Salaam"
      country: "TZ"
      recipientName: "Nuh Test"
    }
  }) {
    success
    duplicate
    errorCode
    message
    order {
      id
      status
      totalAmount
    }
  }
}
```

### Cancel an order
```graphql
mutation Cancel {
  cancelOrder(orderId: "your-order-id-here") {
    success
    message
  }
}
```

### Check queue stats (DEBUG only)
```graphql
query Queues {
  queueStats {
    name
    messages
    consumers
    durable
  }
}
```

---

## Adding a new service endpoint

1. Add a method to the relevant client in `service_clients.py`
2. Add a DTO in `dtos.py` if the response shape is new
3. Add a factory function in `dtos.py` if needed
4. Add/update the Graphene type in `types.py` if new fields are exposed
5. Add the resolver in `queries.py` or `mutations.py`

Only steps 4 and 5 are always required. Steps 1-3 only if truly new.
