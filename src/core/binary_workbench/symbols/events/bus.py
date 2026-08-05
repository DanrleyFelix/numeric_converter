from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from src.core.binary_workbench.symbols.events.models import SymbolEvent


class SymbolEventBus:
    """Publish one post-commit Core event per logical operation."""

    def __init__(self) -> None:
        self._listeners: dict[type[SymbolEvent], list[Callable[[SymbolEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: type[SymbolEvent], listener: Callable[[SymbolEvent], None]) -> None:
        """Register a framework-neutral event listener."""

        self._listeners[event_type].append(listener)

    def publish(self, event: SymbolEvent) -> None:
        """Notify listeners after the owning transaction has committed."""

        for listener in tuple(self._listeners.get(type(event), ())):
            listener(event)
