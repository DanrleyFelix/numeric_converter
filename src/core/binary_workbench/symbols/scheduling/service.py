from __future__ import annotations

from src.core.binary_workbench.symbols.constants import (
    MAX_SYMBOL_BATCH_SIZE,
    MIN_SYMBOL_BATCH_SIZE,
    SCHEDULER_AGING_MS,
    TARGET_BATCH_DURATION_MS,
)
from src.core.binary_workbench.symbols.scheduling.models import SymbolWorkItem


class SymbolWorkScheduler:
    """Order work dynamically and adapt batches to the UI time budget."""

    def __init__(self) -> None:
        self._average_item_ms = 0.25

    def order(self, items: list[SymbolWorkItem], now_ms: float) -> list[SymbolWorkItem]:
        """Recalculate distance and aging priority immediately before a batch."""

        return sorted(items, key=lambda item: self.key(item, now_ms))

    def key(self, item: SymbolWorkItem, now_ms: float) -> tuple[int, int, float, int]:
        """Return priority class, viewport distance, age, and stable sequence."""

        age = max(0.0, now_ms - item.enqueued_ms)
        aged_priority = max(1, int(item.priority) - int(age // SCHEDULER_AGING_MS))
        if int(item.priority) == 0:
            aged_priority = 0
        return aged_priority, max(0, item.distance_from_viewport), -age, item.enqueue_sequence

    def batch_size(self) -> int:
        """Choose at most 256 records for a roughly 65 ms worker slice."""

        estimated = int(TARGET_BATCH_DURATION_MS / max(0.01, self._average_item_ms))
        return min(MAX_SYMBOL_BATCH_SIZE, max(MIN_SYMBOL_BATCH_SIZE, estimated))

    def record(self, item_count: int, elapsed_ms: float) -> None:
        """Update the moving item-cost average after one completed batch."""

        if item_count <= 0 or elapsed_ms < 0:
            return
        measured = elapsed_ms / item_count
        self._average_item_ms = (self._average_item_ms * 0.75) + (measured * 0.25)
