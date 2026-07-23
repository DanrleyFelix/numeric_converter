from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.debugger.models.session import DebuggerRegister


class BWDebuggerRegs(ABC):
    """Define architecture-neutral register discovery and access."""

    @property
    @abstractmethod
    def descriptors(self) -> tuple[DebuggerRegister, ...]:
        """Return registers in the stable order used by clients."""

        raise NotImplementedError

    @property
    @abstractmethod
    def pc_register(self) -> str:
        """Return the canonical program-counter register name."""

        raise NotImplementedError

    @property
    @abstractmethod
    def stack_register(self) -> str:
        """Return the canonical stack register name."""

        raise NotImplementedError

    @abstractmethod
    def register_size(self, name: str) -> int:
        """Return the size in bits of a named register."""

        raise NotImplementedError

    @abstractmethod
    def read(self, name: str) -> int:
        """Read one register using a canonical name or alias."""

        raise NotImplementedError

    @abstractmethod
    def write(self, name: str, value: int) -> None:
        """Write one register while applying its native width."""

        raise NotImplementedError

    @abstractmethod
    def snapshot(self) -> dict[str, int]:
        """Return an independent snapshot keyed by canonical names."""

        raise NotImplementedError

    @abstractmethod
    def reset(self, values: dict[str, int] | None = None) -> None:
        """Reset all registers and optionally apply initial values."""

        raise NotImplementedError

