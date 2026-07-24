from __future__ import annotations

from src.core.debugger.models.session import (
    DebuggerBreakpoint,
    DebuggerEvent,
    DebuggerInstruction,
)


class PsxSessionControlMixin:
    """Manage architecture-neutral breakpoint and ignored metadata."""

    def add_breakpoint(
        self, address: int, enabled: bool = True, name: str = ""
    ) -> DebuggerBreakpoint:
        """Create or replace a breakpoint without changing emulated bytes."""

        instruction = self._instruction_at(address)
        valid = bool(self._image and self._image.contains(address, 4) and instruction)
        breakpoint = DebuggerBreakpoint(
            address,
            enabled,
            instruction.origin if instruction else "",
            instruction.raw_instruction if instruction else "",
            valid,
            name,
        )
        self._breakpoints[address] = breakpoint
        self._events.append(DebuggerEvent("Info", f"Breakpoint added at 0x{address:08X}.", address))
        return breakpoint

    def toggle_breakpoint(self, address: int) -> DebuggerBreakpoint:
        """Toggle breakpoint presence for an instruction address."""

        if address in self._breakpoints:
            self.remove_breakpoint(address)
            return DebuggerBreakpoint(address, False, valid=False)
        return self.add_breakpoint(address)

    def set_breakpoint_enabled(self, address: int, enabled: bool) -> None:
        """Preserve breakpoint metadata while changing its active state."""

        current = self._breakpoints.get(address)
        if current is None:
            current = self.add_breakpoint(address, enabled)
        self._breakpoints[address] = DebuggerBreakpoint(
            current.address,
            enabled,
            current.origin,
            current.instruction,
            current.valid,
            current.name,
        )

    def set_breakpoint_name(self, address: int, name: str) -> None:
        """Update only the symbolic name retained for one breakpoint."""

        current = self._breakpoints.get(address)
        if current is None:
            return
        self._breakpoints[address] = DebuggerBreakpoint(
            current.address,
            current.enabled,
            current.origin,
            current.instruction,
            current.valid,
            name,
        )

    def remove_breakpoint(self, address: int) -> None:
        """Remove one breakpoint without modifying virtual memory."""

        if self._breakpoints.pop(address, None) is not None:
            self._events.append(DebuggerEvent("Info", f"Breakpoint removed at 0x{address:08X}.", address))

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

    def _active_breakpoint(self, address: int) -> DebuggerBreakpoint | None:
        """Return an enabled valid breakpoint at an address."""

        item = self._breakpoints.get(address)
        return item if item and item.enabled and item.valid else None
