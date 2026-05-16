"""
payment_simulator.py
--------------------
Simulates a payment gateway (e.g. Stripe / Flutterwave).

HOW TO CONTROL TEST OUTCOMES
------------------------------
The last digit of the card number determines the result.
This makes your tests fully deterministic — pick the card
number that triggers the scenario you want to test.

    Last digit 0, 5, 6, 8  → success
    Last digit 1            → card declined        (non-retryable)
    Last digit 2            → insufficient funds   (non-retryable)
    Last digit 3, 4         → gateway timeout      (retryable)
    Last digit 7            → network error        (retryable)
    Last digit 9            → fraud blocked        (non-retryable)

USAGE IN YOUR CONSUMER
------------------------
    from simulators.payment_simulator import (
        charge_card, refund_payment,
        RetryablePaymentError, NonRetryablePaymentError,
    )

    try:
        result = charge_card(
            card_number=order_data["card_number"],
            amount=order_data["amount"],        # in smallest unit (cents / fils)
            currency=order_data["currency"],    # e.g. "TZS", "USD"
            order_id=order_data["order_id"],
        )
    except RetryablePaymentError as e:
        # NACK the message — retry logic / DLQ will handle it
        raise
    except NonRetryablePaymentError as e:
        # Publish payment.failed and ACK the message — no retry useful
        publish_payment_failed(order_data["order_id"], str(e))
        return

    if result["status"] == "success":
        publish_payment_succeeded(order_data["order_id"], result)
    else:
        publish_payment_failed(order_data["order_id"], result["error_code"])

SWAPPING IN REAL STRIPE LATER
--------------------------------
Replace the body of charge_card() with a real stripe.PaymentIntent.create()
call. The return dict shape stays identical so nothing else in your codebase
needs to change.
"""

import time
import uuid
import logging
from .Errors import RetryablePaymentError, NonRetryablePaymentError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Card behaviour map — last digit controls outcome
# ---------------------------------------------------------------------------

_CARD_OUTCOMES = {
    "0": "success",
    "1": "declined",
    "2": "insufficient_funds",
    "3": "timeout",
    "4": "timeout",
    "5": "success",
    "6": "success",
    "7": "network_error",
    "8": "success",
    "9": "fraud_blocked",
}

_NON_RETRYABLE_FAILURES = {"declined", "insufficient_funds", "fraud_blocked"}
_RETRYABLE_FAILURES     = {"timeout", "network_error"}

# Simulated gateway latency for successful calls (seconds)
_SIMULATED_LATENCY = 0.4

# Timeout threshold the simulator uses for "timeout" scenario (seconds).
# Set this higher than your consumer's socket timeout so the consumer
# actually times out and raises RetryablePaymentError.
_SIMULATED_TIMEOUT_DELAY = 35

TEST_CARDS = {
        "4111111111110": "Always succeeds",
        "4111111111111": "Card declined (non-retryable)",
        "4111111111112": "Insufficient funds (non-retryable)",
        "4111111111113": "Gateway timeout (retryable — triggers DLQ after 3 attempts)",
        "4111111111114": "Gateway timeout (retryable)",
        "4111111111117": "Network error (retryable)",
        "4111111111119": "Fraud blocked (non-retryable)",
    }

    
class PaymentSimulator:
    @staticmethod
    def charge_card(
        card_number: str,
        amount: int,
        currency: str,
        order_id: str,
    ) -> dict:
        """
        Simulate charging a payment card.

        Parameters
        ----------
        card_number : str
            16-digit card number string. Last digit controls the outcome.
        amount : int
            Charge amount in the smallest currency unit
            (e.g. 150000 for TZS 150,000 or 1500 for USD 15.00).
        currency : str
            ISO 4217 currency code, e.g. "TZS", "USD", "KES".
        order_id : str
            Your internal order UUID. Included in the simulated response
            for traceability — mirrors Stripe's metadata field.

        Returns
        -------
        dict with keys:
            status           : "success" | "failed"
            payment_intent_id: str (sim_pi_...) or None
            amount_charged   : int or None
            currency         : str or None
            error_code       : str or None  (only when status == "failed")
            retryable        : bool

        Raises
        ------
        RetryablePaymentError
            When the gateway times out or has a network error.
        NonRetryablePaymentError
            Should not normally be raised — permanent failures are returned
            as a failed result dict so callers can publish payment.failed
            cleanly. Raised only for unexpected internal errors.
        """
        outcome = _CARD_OUTCOMES.get(card_number.strip()[-1], "success")

        logger.info(
            "payment_simulator.charge_card called",
            extra={
                "order_id": order_id,
                "outcome": outcome,
                "amount": amount,
                "currency": currency,
            },
        )

        # --- Retryable failures: raise so consumer NACKs ---
        if outcome == "timeout":
            logger.warning("payment_simulator: simulating gateway timeout", extra={"order_id": order_id})
            time.sleep(_SIMULATED_TIMEOUT_DELAY)
            raise RetryablePaymentError("Payment gateway did not respond within timeout")

        if outcome == "network_error":
            logger.warning("payment_simulator: simulating network error", extra={"order_id": order_id})
            raise RetryablePaymentError("Could not reach payment gateway — network error")

        # --- Non-retryable failures: return result dict so consumer can ACK ---
        if outcome in _NON_RETRYABLE_FAILURES:
            logger.info(
                "payment_simulator: non-retryable failure",
                extra={"order_id": order_id, "error_code": outcome},
            )
            return {
                "status": "failed",
                "payment_intent_id": None,
                "amount_charged": None,
                "currency": None,
                "error_code": outcome,
                "retryable": False,
            }

        # --- Success ---
        time.sleep(_SIMULATED_LATENCY)  # realistic gateway delay
        payment_intent_id = f"sim_pi_{uuid.uuid4().hex[:16]}"
        logger.info(
            "payment_simulator: charge successful",
            extra={
                "order_id": order_id,
                "payment_intent_id": payment_intent_id,
            },
        )
        return {
            "status": "success",
            "payment_intent_id": payment_intent_id,
            "amount_charged": amount,
            "currency": currency,
            "error_code": None,
            "retryable": False,
        }


    @staticmethod
    def refund_payment(payment_intent_id: str, amount: int) -> dict:
        """
        Simulate refunding a previously successful charge.

        Parameters
        ----------
        payment_intent_id : str
            The payment_intent_id from the original charge_card() response.
        amount : int
            Amount to refund in smallest currency unit.
            Must be <= original charge amount.

        Returns
        -------
        dict with keys:
            status    : "refunded"
            refund_id : str (sim_re_...)
            amount    : int
        """
        if not payment_intent_id or not payment_intent_id.startswith("sim_pi_"):
            raise NonRetryablePaymentError(
                f"Cannot refund: invalid payment_intent_id '{payment_intent_id}'"
            )

        refund_id = f"sim_re_{uuid.uuid4().hex[:16]}"
        logger.info(
            "payment_simulator: refund issued",
            extra={"payment_intent_id": payment_intent_id, "refund_id": refund_id, "amount": amount},
        )
        return {
            "status": "refunded",
            "refund_id": refund_id,
            "amount": amount,
        }


    # ---------------------------------------------------------------------------
    # Test card reference (print this during development)
    # ---------------------------------------------------------------------------

    


    def print_test_cards():
        """Helper — call from a management command or shell to show test cards."""
        print("\n=== Payment Simulator Test Cards ===")
        for card, description in TEST_CARDS.items():
            print(f"  {card}  →  {description}")
        print()
