from __future__ import annotations

from src.core.debugger.backends.hooks.observations import BackendObservation
from src.core.debugger.models.session import DebuggerEvent


class PsxObservationMixin:
    """Collect backend hooks into statistics and debugger log events."""

    def _observe_backend(self, observation: BackendObservation) -> None:
        """Update counters and append a structured event for one hook."""

        if observation.kind == "execute":
            _increment(self._statistics.executed, observation.address)
            return
        if observation.kind == "read":
            _increment(self._statistics.reads, observation.address)
            self._memory_event("Memory", "Read", observation)
            return
        if observation.kind == "write":
            _increment(self._statistics.writes, observation.address)
            self._memory_event("Memory", "Write", observation)
            return
        if observation.kind == "alignment":
            self._memory_event("Alignment Memory Error", "Unaligned access", observation)
            return
        self._memory_event("Error", observation.message or "Invalid memory access", observation)

    def _memory_event(
        self,
        level: str,
        operation: str,
        observation: BackendObservation,
    ) -> None:
        """Record memory context including the responsible instruction."""

        instruction = self._instruction_at(observation.pc or -1)
        details = {
            "size": observation.size,
            "value": observation.value,
            "pc": observation.pc,
            "instruction": instruction.raw_instruction if instruction else "",
        }
        message = f"{operation} at 0x{observation.address:08X} ({observation.size} bytes)."
        self._events.append(DebuggerEvent(level, message, observation.address, details))


def _increment(values: dict[int, int], address: int) -> None:
    """Increment one address-indexed statistics counter."""

    values[address] = values.get(address, 0) + 1
