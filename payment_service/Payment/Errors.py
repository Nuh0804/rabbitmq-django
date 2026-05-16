
class RetryablePaymentError(Exception):
    """
    Transient error — the gateway may succeed if tried again.
    Your consumer should NACK the message and let the retry/DLQ
    mechanism handle it.
    """
    pass


class NonRetryablePaymentError(Exception):
    """
    Permanent error — retrying will not help.
    Your consumer should publish payment.failed and ACK the message.
    """
    pass
