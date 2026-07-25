from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.debugger.models.session import DebuggerBreakpoint


class BWDebuggerControl(ABC):
    """Define optional execution-control metadata shared across architectures."""

    @abstractmethod
    def step_over(self, limit: int | None = None) -> None:
        """Execute one normal instruction or run through a call."""

        raise NotImplementedError

    @abstractmethod
    def add_breakpoint(
        self,
        address: int,
        enabled: bool = True,
        name: str = "",
        breakpoint_type: str = "execution",
    ) -> DebuggerBreakpoint:
        """Add typed non-invasive breakpoint metadata for one address."""

        raise NotImplementedError

    @abstractmethod
    def add_register_breakpoint(
        self,
        condition: str,
        enabled: bool = True,
        name: str = "",
    ) -> DebuggerBreakpoint:
        """Add a standalone conditional register breakpoint."""

        raise NotImplementedError

    @abstractmethod
    def toggle_breakpoint(self, address: int) -> DebuggerBreakpoint:
        """Toggle breakpoint presence for one address."""

        raise NotImplementedError

    @abstractmethod
    def set_breakpoint_enabled(self, identifier: int, enabled: bool) -> None:
        """Enable or disable retained breakpoint metadata."""

        raise NotImplementedError

    @abstractmethod
    def set_breakpoint_name(self, identifier: int, name: str) -> None:
        """Assign a symbolic display name to retained breakpoint metadata."""

        raise NotImplementedError

    @abstractmethod
    def set_breakpoint_type(self, identifier: int, expression: str) -> None:
        """Apply one valid type combination to retained breakpoint metadata."""

        raise NotImplementedError

    @abstractmethod
    def set_breakpoint_where(self, identifier: int, expression: str) -> None:
        """Update and validate the effective breakpoint condition."""

        raise NotImplementedError

    @abstractmethod
    def remove_breakpoint(self, identifier: int) -> None:
        """Remove breakpoint metadata without changing virtual memory."""

        raise NotImplementedError

    @property
    @abstractmethod
    def ignored_instructions(self) -> frozenset[int]:
        """Return explicitly ignored instruction addresses."""

        raise NotImplementedError

    @property
    @abstractmethod
    def ignored_addresses(self) -> frozenset[int]:
        """Return control-flow destinations ignored by session directives."""

        raise NotImplementedError

    @abstractmethod
    def toggle_ignored_instruction(self, address: int) -> bool:
        """Toggle explicit IGNORED state for one instruction."""

        raise NotImplementedError

    @abstractmethod
    def clear_events(self) -> None:
        """Clear log events without changing execution statistics."""

        raise NotImplementedError

    @abstractmethod
    def record_event(self, level: str, message: str) -> None:
        """Record one controlled lifecycle event."""

        raise NotImplementedError

    @abstractmethod
    def update_instruction(
        self,
        address: int,
        data: bytes,
        raw_instruction: str,
        status: str = "Ready",
    ) -> None:
        """Refresh volatile instruction metadata after memory edits."""

        raise NotImplementedError
