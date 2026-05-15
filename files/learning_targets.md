# RabbitMQ E-Commerce Project — Learning Targets

> Organised by priority. Complete each layer before moving to the next.
> Each target includes what to learn, where it appears in the project, and what competence looks like.

---

## Layer 1 — Must know before writing code

### L1-01 · Docker & Docker Compose
**What to learn:** Dockerfile per service, docker-compose.yml with separate ports and networks, volumes, environment variables, healthchecks, `depends_on`.
**Where it appears:** Running 6 services + RabbitMQ + multiple databases locally simultaneously.
**Competence:** You can bring the full stack up with one command and each service is reachable on its own port.

---

### L1-02 · PostgreSQL transactions in Django ORM
**What to learn:** `select_for_update()` for row-level locking, `transaction.atomic()` blocks, `on_commit()` hook.
**Where it appears:** Inventory stock deduction (concurrent orders), outbox pattern (publish inside same transaction as DB write).
**Competence:** You can wrap a DB write and a queue publish atomically so neither succeeds without the other.

---

### L1-03 · pika — Python AMQP client
**What to learn:** `BlockingConnection`, `channel.basic_publish()`, `basic_consume()`, `basic_ack()`, `basic_nack()`, `basic_qos()`.
**Where it appears:** Every service consumer and publisher.
**Competence:** You can declare an exchange and queue, publish a persistent message, and write a consumer that manually ACKs.

---

### L1-04 · Django management commands for consumers
**What to learn:** `BaseCommand`, `handle()`, running long-lived processes alongside gunicorn.
**Where it appears:** Each service has one or more `python manage.py consume_*` workers.
**Competence:** You can write a blocking consumer loop as a management command and run it as a separate Docker process.

---

### L1-05 · Environment-based configuration
**What to learn:** `.env` files, `python-decouple`, never hardcoding connection strings.
**Where it appears:** All service URLs, RabbitMQ URL, DB URL, JWT secret.
**Competence:** Swapping from localhost to Docker network URLs requires only a `.env` change.

---

## Layer 2 — Core patterns (learn as you build)

### L2-01 · Idempotency key pattern
**What to learn:** `idempotency_keys` table design, unique constraint on `(order_id, event_type)`, `get_or_create()` pattern.
**Where it appears:** Every consumer — payment, inventory, shipping, notification.
**Competence:** A message delivered twice produces exactly one DB write and one downstream action.

---

### L2-02 · Transactional outbox pattern
**What to learn:** Outbox table written inside the same `transaction.atomic()` as the business record; background thread reads unpublished rows and publishes them.
**Where it appears:** Order Service publishing `order.created`, Payment Service publishing `payment.succeeded`.
**Competence:** The app can crash between a DB write and a broker publish without losing the message.

---

### L2-03 · Dead Letter Queue + retry with exponential backoff
**What to learn:** `x-dead-letter-exchange` header, `x-message-ttl` on retry queue, NACK with `requeue=False`, retry counter in message headers.
**Where it appears:** Payment consumer (Stripe timeout), Shipping consumer (courier API down), Notification consumer (email provider down).
**Competence:** A failing message retries 3 times with increasing delay then lands in a DLQ without blocking the queue.

---

### L2-04 · RabbitMQ exchange types
**What to learn:** Topic exchange (routing by pattern), fanout exchange (broadcast), direct exchange (exact key), dead letter exchange.
**Where it appears:** `order.topic` routes `order.created/paid/cancelled`; `notifications.fanout` broadcasts to email and SMS queues simultaneously.
**Competence:** You can explain why each exchange type was chosen and configure them in code.

---

### L2-05 · Saga pattern — choreography-based compensation
**What to learn:** Each service listens for its trigger event, does its work, publishes its outcome; compensation events undo completed steps when a later step fails.
**Where it appears:** Payment failed → inventory not touched. Stock failed → payment refunded. Shipment cancelled → stock released.
**Competence:** You can draw the full compensation map for the order flow on paper before writing any code.

---

### L2-06 · Order state machine
**What to learn:** Valid state transitions, rejecting backwards transitions, `django-fsm` or manual transition guards.
**Where it appears:** Order Service — status must follow: pending → payment_processing → paid → fulfilling → shipped.
**Competence:** An event cannot move an order to an invalid state; the model raises an error if attempted.

---

### L2-07 · Optimistic and pessimistic locking
**What to learn:** `select_for_update()` (pessimistic), version field + `OperationalError` (optimistic), retry logic around lock failures.
**Where it appears:** Inventory Service — two workers racing to deduct the last unit.
**Competence:** Concurrent stock deduction never produces a negative stock level.

---

### L2-08 · pytest for consumer testing
**What to learn:** pytest fixtures, `conftest.py`, mocking pika channels with `unittest.mock`, testing management commands, integration tests against a real RabbitMQ container.
**Where it appears:** Every test case in the test cases document.
**Competence:** You can publish a test message and assert the resulting DB state without a running frontend.

---

### L2-09 · Correlation IDs and structured logging
**What to learn:** UUID generated at order creation, passed as a pika message header, logged with every action across every service, `structlog` or `python-json-logger`.
**Where it appears:** OPS-02 — reconstructing the full trace of a failed order across 4 services.
**Competence:** You can grep one correlation_id across all service logs and see the complete timeline.

---

## Layer 3 — Production quality (after core flow works)

### L3-01 · Health check endpoints + consumer lag monitoring
**What to learn:** RabbitMQ Management HTTP API (`/api/queues/`), reporting `consumer_lag`, `last_processed_at`, DB and broker connection status.
**Where it appears:** OPS-01 — detecting a stuck consumer within 60 seconds.
**Competence:** Docker and monitoring tools can determine service health without reading logs.

---

### L3-02 · Celery beat for scheduled jobs
**What to learn:** `celery beat`, `CELERY_BEAT_SCHEDULE`, periodic tasks using RabbitMQ as broker.
**Where it appears:** Reconciliation job (DATA-01, DATA-04), reservation TTL expiry (INV-06), outbox publisher loop.
**Competence:** Scheduled jobs run on a configurable interval and can be observed via Celery logs.

---

### L3-03 · Circuit breaker pattern
**What to learn:** `pybreaker`, `CircuitBreaker` class, open/closed/half-open states, integrating with the consumer loop.
**Where it appears:** Payment Service — Stripe repeatedly down; prevents tight retry loop flooding the DLQ.
**Competence:** After N consecutive failures the consumer pauses automatically and resumes after a cooldown.

---

### L3-04 · JSON Schema message validation
**What to learn:** `jsonschema`, `Draft7Validator`, schema versioning with a `version` field in every message.
**Where it appears:** DATA-06 — producer adds a new field; old consumer must not crash.
**Competence:** Every message is validated against a schema before processing; invalid messages are rejected with a clear error.

---

### L3-05 · Message priority queues
**What to learn:** `x-max-priority` queue argument, setting `priority` property on published messages, worker behaviour under mixed priority load.
**Where it appears:** Shipping Service — premium orders (priority=10) processed before standard (priority=1).
**Competence:** Under load, high-priority messages drain first regardless of arrival order.

---

### L3-06 · Competing consumers and prefetch count
**What to learn:** Multiple workers on the same queue, `basic_qos(prefetch_count=1)` for fair dispatch, observing worker utilisation.
**Where it appears:** BROKER-06, PERF-02 — 3 Inventory Service workers; killing one mid-consume.
**Competence:** You can explain what happens to unACKed messages when a worker dies and verify redelivery.

---

### L3-07 · RPC over RabbitMQ
**What to learn:** `reply_to` queue, `correlation_id` property, temporary exclusive queues, timeout handling.
**Where it appears:** Order Service waiting for a synchronous payment confirmation before returning HTTP 201.
**Competence:** You can implement a request-reply pattern over RabbitMQ and handle the case where no reply arrives within the timeout.

---

## Summary checklist

```
Layer 1 — Foundation
  [ ] L1-01  Docker & Docker Compose
  [ ] L1-02  PostgreSQL transactions in Django ORM
  [ ] L1-03  pika — Python AMQP client
  [ ] L1-04  Django management commands for consumers
  [ ] L1-05  Environment-based configuration

Layer 2 — Core patterns
  [ ] L2-01  Idempotency key pattern
  [ ] L2-02  Transactional outbox pattern
  [ ] L2-03  Dead Letter Queue + retry with exponential backoff
  [ ] L2-04  RabbitMQ exchange types
  [ ] L2-05  Saga pattern — compensation chains
  [ ] L2-06  Order state machine
  [ ] L2-07  Optimistic and pessimistic locking
  [ ] L2-08  pytest for consumer testing
  [ ] L2-09  Correlation IDs and structured logging

Layer 3 — Production quality
  [ ] L3-01  Health check endpoints + consumer lag monitoring
  [ ] L3-02  Celery beat for scheduled jobs
  [ ] L3-03  Circuit breaker pattern
  [ ] L3-04  JSON Schema message validation
  [ ] L3-05  Message priority queues
  [ ] L3-06  Competing consumers and prefetch count
  [ ] L3-07  RPC over RabbitMQ
```
