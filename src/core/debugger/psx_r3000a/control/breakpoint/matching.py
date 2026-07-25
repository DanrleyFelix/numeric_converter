"""Runtime matching helpers for typed PSX breakpoints."""

from src.core.debugger.breakpoints.types import (
    DEFAULT_BREAKPOINT_TYPE,
    breakpoint_type_tokens,
)
from src.core.debugger.models.session import DebuggerBreakpoint


class PsxBreakpointMatchingMixin:
    """Resolve stored breakpoint metadata for execution and memory events."""

    def _active_breakpoint(self, address: int) -> DebuggerBreakpoint | None:
        """Return an enabled execution breakpoint at one instruction address."""

        item = self._breakpoints.get(address)
        active = item and DEFAULT_BREAKPOINT_TYPE in breakpoint_type_tokens(
            item.breakpoint_type
        )
        return item if active and item.enabled and item.valid else None

    def _active_memory_breakpoint(
        self, operation: str, address: int, size: int
    ) -> DebuggerBreakpoint | None:
        """Return the first access breakpoint overlapping an observed interval."""

        for item in self._breakpoints.values():
            if (
                item.address is not None
                and item.enabled
                and item.valid
                and operation in breakpoint_type_tokens(item.breakpoint_type)
                and address <= item.address < address + max(1, size)
            ):
                return item
        return None

    def _breakpoint_for(self, identifier: int) -> DebuggerBreakpoint | None:
        """Return breakpoint metadata by its stable internal identifier."""

        return self._breakpoints.get(identifier)
