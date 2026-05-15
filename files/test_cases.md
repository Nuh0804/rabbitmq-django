# RabbitMQ E-Commerce Project — Test Cases

> **Severity levels**
> `CRITICAL` — data corruption or permanent loss if failed
> `HIGH` — visible degradation or incorrect business outcome
> `MEDIUM` — correctness or observability concern
> `LOW` — config hygiene or nice-to-have behaviour

---

## Order Service

| ID | Severity | Test Case |
|----|----------|-----------|
| ORD-01 | CRITICAL | **Duplicate order submission** — two identical POST /orders/ within 500ms with same cart and user returns 409 with existing order_id; DB has exactly one row |
| ORD-02 | CRITICAL | **Order published but DB write fails** — simulated DB timeout after publish; message must NOT be published; no orphan message in queue |
| ORD-03 | HIGH | **Order created with zero items** — empty items array returns 422; no message published; no DB row created |
| ORD-04 | HIGH | **Order cancelled mid-flight** — order.created already published; Payment Service checks order status before charging and skips; order status = cancelled |
| ORD-05 | MEDIUM | **Order status reflects full lifecycle** — status transitions: pending → payment_processing → paid → fulfilling → shipped; no skipped states |
| ORD-06 | MEDIUM | **Order for out-of-stock item** — returns 400 immediately; no message published; no charge attempted |

---

## Payment Service

| ID | Severity | Test Case |
|----|----------|-----------|
| PAY-01 | CRITICAL | **Consumer receives same message twice** — network blip causes redelivery before ACK; idempotency key prevents double charge; payment table has exactly one row for that order_id |
| PAY-02 | CRITICAL | **Card charge succeeds but ACK lost** — Stripe returns success; consumer crashes before basic_ack(); redelivery finds existing payment row; skips charge; ACKs; no second charge |
| PAY-03 | CRITICAL | **Card declined** — publishes payment.failed; Order Service sets order status = payment_failed; inventory not touched; shipping not triggered |
| PAY-04 | CRITICAL | **Payment Service is down when order is created** — message sits in durable queue; on restart service processes message and completes flow; no message lost |
| PAY-05 | HIGH | **Stripe API timeout on first attempt** — message NACKed and requeued; retried up to 3 times with backoff; after 3 failures goes to payment.dlq; order status = payment_failed |
| PAY-06 | HIGH | **Partial payment amount** — amount=0 rejected by downstream validation; alert raised; order held for manual review |
| PAY-07 | HIGH | **Currency mismatch between order and payment** — currency code validated; mismatch raises alert |
| PAY-08 | MEDIUM | **Refund triggers compensation chain** — payment.refunded published; Inventory releases reservation if held; Shipping cancels if not dispatched; Notification sends refund email |
| PAY-09 | MEDIUM | **DLQ message replayed after fix** — message re-published to payment.queue; processed successfully; order completes normally |

---

## Inventory Service

| ID | Severity | Test Case |
|----|----------|-----------|
| INV-01 | CRITICAL | **Double stock deduction from redelivery** — crash after deduction before ACK; redelivery finds idempotency record; skips second deduction |
| INV-02 | CRITICAL | **Concurrent orders for last unit in stock** — two payment.succeeded arrive simultaneously; DB row-level lock ensures only one deduction; second gets stock.failed |
| INV-03 | CRITICAL | **Service down when payment succeeded** — message retained in durable queue; on restart stock deducted; flow continues |
| INV-04 | HIGH | **Stock goes negative** — DB constraint rejects; NACK no-requeue; goes to DLQ; alert raised |
| INV-05 | HIGH | **Stock reserved but shipment never created** — message retained in shipping.queue; on restart Shipping processes it; stock remains reserved |
| INV-06 | MEDIUM | **Stock reservation expires without shipment** — TTL elapses; scheduled job releases reservation; order set to fulfillment_failed; notification sent |
| INV-07 | MEDIUM | **Multiple items in one order** — all deductions atomic; if any fails all rolled back; stock.failed published |

---

## Shipping Service

| ID | Severity | Test Case |
|----|----------|-----------|
| SHIP-01 | CRITICAL | **Duplicate shipment for same order** — stock.reserved redelivered; idempotency check prevents second shipment row; only one shipment.created published |
| SHIP-02 | HIGH | **Service down when stock reserved** — message durable; on restart Shipping processes it; no message lost |
| SHIP-03 | HIGH | **Courier API is down** — NACK; retry with exponential backoff; after 3 failures goes to DLQ; alert to ops |
| SHIP-04 | MEDIUM | **Shipping address invalid** — non-retryable rejection; NACKed no-requeue; DLQ; user notified for address correction |
| SHIP-05 | MEDIUM | **Tracking number not generated** — validation before publish raises error; retried; after 3 tries ops alerted |
| SHIP-06 | LOW | **Priority queue ordering** — premium order (priority=10) consumed before standard (priority=1) regardless of arrival order |

---

## Notification Service

| ID | Severity | Test Case |
|----|----------|-----------|
| NOTIF-01 | HIGH | **Service down for 24 hours** — messages with valid TTL processed on restart; expired messages discarded to DLQ; no stale emails sent |
| NOTIF-02 | HIGH | **Email provider is down** — NACK with backoff; after 3 fails moves to DLQ; does not block other notifications |
| NOTIF-03 | MEDIUM | **User receives duplicate emails** — payment.succeeded redelivered; deduplication by event_id in Redis prevents second send |
| NOTIF-04 | MEDIUM | **Fanout reaches both email and SMS queues** — failure of one channel does not affect the other; independent queues |
| NOTIF-05 | LOW | **User has opted out of SMS** — SMS worker checks preference; skips send; ACKs normally; no error raised |

---

## RabbitMQ Broker

| ID | Severity | Test Case |
|----|----------|-----------|
| BROKER-01 | CRITICAL | **RabbitMQ restarts mid-flow** — durable queues and persistent messages survive restart; consumers resume; no messages lost |
| BROKER-02 | CRITICAL | **Message published without persistence flag** — all messages on payment.queue and inventory.queue must be delivery_mode=2; fail build if not |
| BROKER-03 | HIGH | **Queue fills up (consumer lag)** — queue depth exceeds 10,000; alert fires; back-pressure or additional workers triggered |
| BROKER-04 | HIGH | **Dead letter queue fills with no consumer** — alert fires after DLQ depth > 50; DLQ must always have a monitoring consumer |
| BROKER-05 | MEDIUM | **Connection loss during publish** — ConnectionClosed raised; Order Service retries with backoff; message eventually published; no duplicate |
| BROKER-06 | MEDIUM | **Consumer prefetch starvation** — prefetch_count=0 starves other workers; test asserts prefetch_count=1 on all consumers |

---

## Data Consistency

| ID | Severity | Test Case |
|----|----------|-----------|
| DATA-01 | CRITICAL | **Order paid but stock never deducted** — reconciliation job detects orders in paid status with no reservation row; alert ops |
| DATA-02 | CRITICAL | **Stock deducted but payment failed** — payment.failed triggers stock.released; stock restored; order cancelled |
| DATA-03 | CRITICAL | **Outbox: message lost between DB and broker** — crash between DB write and publish; outbox table has unpublished row; background publisher picks it up |
| DATA-04 | HIGH | **Cross-service data mismatch audit** — order=paid in Order Service but no payment row in Payment Service; mismatch detected and alerted |
| DATA-05 | HIGH | **Event ordering violation** — payment.failed arrives before payment.succeeded; state machine uses timestamps; rejects backwards transitions |
| DATA-06 | MEDIUM | **Message schema change breaks consumer** — new required field added; old consumer handles missing field gracefully; no crash or NACK loop |

---

## Performance & Load

| ID | Severity | Test Case |
|----|----------|-----------|
| PERF-01 | HIGH | **100 concurrent orders** — no duplicate charges; stock count mathematically correct; zero messages lost |
| PERF-02 | HIGH | **Consumer restart during high load** — 500 messages in queue; one of 3 instances killed; unACKed messages redelivered; no loss or double-processing |
| PERF-03 | MEDIUM | **Slow consumer does not block fast consumer** — SMS (2s/msg) and email (50ms/msg) have independent queues; no cross-blocking |
| PERF-04 | MEDIUM | **Message TTL does not cause silent data loss** — expired messages route to notify.dlq via dead-letter-exchange; not silently dropped |

---

## Security

| ID | Severity | Test Case |
|----|----------|-----------|
| SEC-01 | HIGH | **Unauthenticated publish to queue** — direct AMQP connection without credentials rejected; vhost permissions enforced |
| SEC-02 | HIGH | **Message payload injection** — malicious order_id value treated as data not code; parameterised queries used; processed or rejected cleanly |
| SEC-03 | MEDIUM | **Sensitive data in message body** — full card number not present in message; only last 4 digits and payment_intent_id |

---

## Observability & Ops

| ID | Severity | Test Case |
|----|----------|-----------|
| OPS-01 | HIGH | **No health endpoint on consumer** — stuck consumer detected within 60s via /health/ reporting consumer_lag, last_processed_at, retry_count |
| OPS-02 | MEDIUM | **End-to-end trace across services** — same correlation_id appears in logs of all 4 services; full trace reconstructable |
| OPS-03 | MEDIUM | **DLQ replay does not create duplicates** — 10 messages replayed; idempotency check fires; exactly 10 payments processed; 0 duplicates |
| OPS-04 | LOW | **Message rate metrics exported** — publish_rate, consume_rate, dlq_depth, consumer_lag all visible in Grafana during load test |
