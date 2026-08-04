from __future__ import annotations

from threading import Event


class CancellationToken:
    """Provide cooperative cancellation without terminating worker threads."""

    def __init__(self) -> None:
        self._cancelled = Event()

    def cancel(self) -> None:
        """Mark the associated calculation as obsolete."""

        self._cancelled.set()

    def is_cancelled(self) -> bool:
        """Return whether a caller should abandon its current calculation."""

        return self._cancelled.is_set()
