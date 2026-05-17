class ReservationFailedError(Exception):
    """Raised inside transaction.atomic() to trigger rollback on reservation failure."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Reservation failed with code {code}")