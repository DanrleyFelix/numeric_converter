from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.debugger.contracts.registers import BWDebuggerRegs
from src.core.debugger.contracts.session.control import BWDebuggerControl
from src.core.debugger.models.session import (
    DebuggerBreakpoint,
    DebuggerEndianness,
    DebuggerError,
    DebuggerEvent,
    DebuggerInstruction,
    DebuggerSessionState,
    DebuggerStatistics,
    DebuggerStepRules,
)


class BWDebugger(BWDebuggerControl, ABC):
    """Define the architecture-neutral debugger session contract."""

    @property
    @abstractmethod
    def architecture(self) -> str:
        """Return the backend architecture display name."""

        raise NotImplementedError

    @property
    @abstractmethod
    def endianness(self) -> DebuggerEndianness:
        """Return the backend byte order."""

        raise NotImplementedError

    @property
    @abstractmethod
    def registers(self) -> BWDebuggerRegs:
        """Return the register access contract for this session."""

        raise NotImplementedError

    @property
    @abstractmethod
    def step_rules(self) -> DebuggerStepRules:
        """Return architecture-specific stepping metadata."""

        raise NotImplementedError

    @property
    @abstractmethod
    def state(self) -> DebuggerSessionState:
        """Return the current session lifecycle state."""

        raise NotImplementedError

    @property
    @abstractmethod
    def pc(self) -> int:
        """Read the program counter through the register contract."""

        raise NotImplementedError

    @pc.setter
    @abstractmethod
    def pc(self, value: int) -> None:
        """Write the program counter through the register contract."""

        raise NotImplementedError

    @property
    @abstractmethod
    def breakpoints(self) -> tuple[DebuggerBreakpoint, ...]:
        """Return all active and inactive breakpoint metadata."""

        raise NotImplementedError

    @property
    @abstractmethod
    def statistics(self) -> DebuggerStatistics:
        """Return execution and memory counters."""

        raise NotImplementedError

    @property
    @abstractmethod
    def instructions(self) -> tuple[DebuggerInstruction, ...]:
        """Return the instructions known by the current image."""

        raise NotImplementedError

    @property
    @abstractmethod
    def events(self) -> tuple[DebuggerEvent, ...]:
        """Return controlled execution and diagnostic events."""

        raise NotImplementedError

    @property
    @abstractmethod
    def last_error(self) -> DebuggerError | None:
        """Return the last controlled error, when one exists."""

        raise NotImplementedError

    @property
    @abstractmethod
    def execution_interval_ms(self) -> int:
        """Return the delay between continuously executed instructions."""

        raise NotImplementedError

    @abstractmethod
    def set_execution_interval(self, interval_ms: int) -> None:
        """Configure continuous execution pacing in milliseconds."""

        raise NotImplementedError

    @abstractmethod
    def read_memory(self, address: int, size: int) -> bytes:
        """Read bytes from the isolated virtual memory image."""

        raise NotImplementedError

    @abstractmethod
    def write_memory(self, address: int, data: bytes) -> None:
        """Write bytes only to the isolated virtual memory image."""

        raise NotImplementedError

    @abstractmethod
    def step(self) -> None:
        """Execute one architecture instruction."""

        raise NotImplementedError

    @abstractmethod
    def run(self, limit: int | None = None) -> None:
        """Execute continuously until a controlled stop condition."""

        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        """Pause execution while preserving volatile state."""

        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop execution while preserving the final state for inspection."""

        raise NotImplementedError

    @abstractmethod
    def restart(self) -> None:
        """Restore the initial session image and registers."""

        raise NotImplementedError
