from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


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

    def editor_command_names(self) -> tuple[str, ...]:
        return ()

    def editor_command_output(
        self,
        name: str,
        args: list[str],
    ) -> list[str] | None:
        return None

    def instruction_code(self, text: str) -> str:
        return text.strip()

    def build_source_line_rows(
        self,
        lines: list[str],
        offset_names: list[str],
        offset_bases: dict[str, str],
        start_offset: int = 0,
        labels: dict[str, str] | None = None,
        variables: dict[str, str] | None = None,
        equates: dict[str, str] | None = None,
        reject_invalid: bool = False,
    ) -> list["BinaryWorkbenchRowDTO"] | None:
        return None
