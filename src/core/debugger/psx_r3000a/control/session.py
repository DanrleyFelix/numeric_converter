from __future__ import annotations

from src.core.debugger.models.session import DebuggerEvent, DebuggerInstruction
from src.core.debugger.psx_r3000a.control.breakpoint.management import (
    PsxBreakpointControlMixin,
)


class PsxSessionControlMixin(PsxBreakpointControlMixin):
    """Manage architecture-neutral breakpoint and ignored metadata."""

    def toggle_ignored_instruction(self, address: int) -> bool:
        """Toggle one visible instruction's explicit IGNORED state."""

        if address in self._ignored_instructions:
            self._ignored_instructions.remove(address)
            ignored = False
        else:
            self._ignored_instructions.add(address)
            ignored = True
        label = "marked IGNORED" if ignored else "restored"
        self._events.append(DebuggerEvent("Info", f"Instruction 0x{address:08X} {label}.", address))
        return ignored

    @property
    def ignored_instructions(self) -> frozenset[int]:
        """Return dynamically ignored instruction addresses."""

        return frozenset(self._ignored_instructions)

    @property
    def ignored_addresses(self) -> frozenset[int]:
        """Return immutable control-flow destinations declared as ignored."""

        return self._image.ignored_addresses if self._image else frozenset()

    def clear_events(self) -> None:
        """Clear the debug log without changing statistics."""

        self._events.clear()

    def record_event(self, level: str, message: str) -> None:
        """Append one lifecycle event requested by a presentation boundary."""

        self._events.append(DebuggerEvent(level, message))

    def update_instruction(
        self,
        address: int,
        data: bytes,
        raw_instruction: str,
        status: str = "Ready",
    ) -> None:
        """Refresh volatile disassembly metadata after an in-memory edit."""

        updated = []
        for item in self._instructions:
            if item.address == address:
                item = DebuggerInstruction(address, data, raw_instruction, item.origin, status)
            updated.append(item)
        self._instructions = tuple(updated)

    def _instruction_at(self, address: int):
        """Return instruction metadata for one exact virtual address."""

        return next((item for item in self._instructions if item.address == address), None)
