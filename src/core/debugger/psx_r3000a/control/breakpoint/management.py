"""Typed breakpoint lifecycle for PSX debugger sessions."""

from __future__ import annotations

from src.core.debugger.breakpoints.conditions import parse_register_condition
from src.core.debugger.breakpoints.types import (
    DEFAULT_BREAKPOINT_TYPE,
    REGISTER_BREAKPOINT_TYPE,
    breakpoint_type_tokens,
    normalize_breakpoint_type,
)
from src.core.debugger.models.session import DebuggerBreakpoint, DebuggerEvent
from src.core.debugger.psx_r3000a.control.breakpoint.editing.session import (
    PsxBreakpointEditingMixin,
)
from src.core.debugger.psx_r3000a.control.breakpoint.matching import (
    PsxBreakpointMatchingMixin,
)


class PsxBreakpointControlMixin(
    PsxBreakpointEditingMixin,
    PsxBreakpointMatchingMixin,
):
    """Create and update execution, access and register breakpoints."""

    def add_breakpoint(
        self,
        address: int,
        enabled: bool = True,
        name: str = "",
        breakpoint_type: str = DEFAULT_BREAKPOINT_TYPE,
    ) -> DebuggerBreakpoint:
        """Create or replace one address-based typed breakpoint."""

        normalized = normalize_breakpoint_type(breakpoint_type)
        tokens = breakpoint_type_tokens(normalized)
        if REGISTER_BREAKPOINT_TYPE in tokens:
            raise ValueError("Use add_register_breakpoint for register conditions.")
        instruction = self._instruction_at(address)
        in_memory = bool(self._image and self._image.contains(address))
        valid = in_memory and (
            tokens != frozenset({DEFAULT_BREAKPOINT_TYPE})
            or instruction is not None
        )
        breakpoint = DebuggerBreakpoint(
            address=address,
            enabled=enabled,
            origin=instruction.origin if instruction else "",
            instruction=instruction.raw_instruction if instruction else "-",
            valid=valid,
            name=name,
            breakpoint_type=normalized,
            where=f"0x{address:08X}",
            identifier=address,
        )
        self._breakpoints[address] = breakpoint
        self._events.append(
            DebuggerEvent("Info", f"Breakpoint added at 0x{address:08X}.", address)
        )
        return breakpoint

    def add_register_breakpoint(
        self,
        condition: str,
        enabled: bool = True,
        name: str = "",
    ) -> DebuggerBreakpoint:
        """Create a validated standalone register-condition breakpoint."""

        where = condition.strip()
        parse_register_condition(where, self._register_aliases)
        identifier = self._next_breakpoint_identifier
        self._next_breakpoint_identifier -= 1
        breakpoint = DebuggerBreakpoint(
            address=None,
            enabled=enabled,
            instruction="-",
            name=name,
            breakpoint_type=REGISTER_BREAKPOINT_TYPE,
            where=where,
            identifier=identifier,
        )
        self._breakpoints[identifier] = breakpoint
        self._events.append(
            DebuggerEvent("Info", f"Register breakpoint added: {where}.")
        )
        return breakpoint

    def toggle_breakpoint(self, address: int) -> DebuggerBreakpoint:
        """Toggle one default execution breakpoint by instruction address."""

        existing = next(
            (
                item
                for item in self._breakpoints.values()
                if item.address == address
            ),
            None,
        )
        if existing is not None:
            self.remove_breakpoint(existing.identifier)
            return DebuggerBreakpoint(
                address,
                False,
                valid=False,
                where=f"0x{address:08X}",
                identifier=address,
            )
        return self.add_breakpoint(address)

    def remove_breakpoint(self, identifier: int) -> None:
        """Remove one breakpoint without modifying virtual memory."""

        current = self._breakpoints.pop(identifier, None)
        if current is None:
            return
        message = (
            f"Breakpoint removed at 0x{current.address:08X}."
            if current.address is not None
            else f"Register breakpoint removed: {current.where}."
        )
        self._events.append(DebuggerEvent("Info", message, current.address))
