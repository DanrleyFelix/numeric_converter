from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from src.core.binary_workbench.symbols.definitions import ProcessingClass


class WorkPriority(IntEnum):
    """Order barrier, viewport, dependencies, and late cache work."""

    BARRIER_OR_EDITED_LINE = 0
    VIEWPORT = 1
    DIRECTIONAL_PREFETCH = 2
    ACTIVE_DEPENDENCIES = 3
    ACTIVE_DIRTY_REMAINDER = 4
    LATE_CACHE = 5


@dataclass(frozen=True, slots=True)
class SymbolWorkItem:
    """Describe one scheduler item without binding Core to Qt."""

    priority: WorkPriority
    distance_from_viewport: int
    enqueued_ms: float
    enqueue_sequence: int
    processing_class: ProcessingClass = ProcessingClass.ORDINARY
    extraordinary_reason: str = ""

    def __post_init__(self) -> None:
        if (
            self.processing_class is ProcessingClass.EXTRAORDINARY
            and not self.extraordinary_reason.strip()
        ):
            raise ValueError("Extraordinary work requires a recorded justification.")
