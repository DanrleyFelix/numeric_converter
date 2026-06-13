from __future__ import annotations

from abc import ABC, abstractmethod


class CPUArchCodec(ABC):
    """
    Small abstraction for CPU architecture codecs.

    This is intentionally limited to a real variation point of the project:
    different CPU architectures can expose the same assemble/disassemble
    contract while keeping their own concrete encoding rules.
    """

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def word_size(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def default_reference_offsets(self) -> tuple[str, ...]:
        raise NotImplementedError

    @abstractmethod
    def assemble(self, instruction: str, address: int) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    def disassemble(self, data: bytes, address: int) -> str:
        raise NotImplementedError

    @abstractmethod
    def bytes_text(self, data: bytes) -> str:
        raise NotImplementedError

    def jump_navigation_target(
        self,
        instruction: str,
        operand: str,
        symbols: dict[str, str] | None = None,
    ) -> int | None:
        return None
