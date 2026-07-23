from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@dataclass(frozen=True)
class DebuggerAssemblySource:
    """Provide one assembly source together with its workspace environment."""

    path: Path
    workspace: str | None
    lines: tuple[str, ...]
    architecture: str
    labels: dict[str, str]
    variables: dict[str, str]
    equates: dict[str, str]

    @property
    def symbols(self) -> dict[str, str]:
        """Return all source Symbol spellings accepted by directives."""

        values = dict(self.labels)
        for name, value in self.variables.items():
            normalized = name.lstrip("_")
            values[normalized] = value
            values[f"_{normalized}"] = value
        for name, value in self.equates.items():
            normalized = name.lstrip("@")
            values[normalized] = value
            values[f"@{normalized}"] = value
        return values


@dataclass(frozen=True)
class DebuggerResolvedImport:
    """Hold one fully assembled import ready for virtual memory loading."""

    path: Path
    workspace: str | None
    architecture: str
    address: int
    data: bytes
    origin: str
    rows: tuple[BinaryWorkbenchRowDTO, ...]

    @property
    def size(self) -> int:
        """Return the number of assembled bytes in this import."""

        return len(self.data)

    @property
    def end(self) -> int:
        """Return the inclusive final address occupied by this import."""

        return self.address + max(0, self.size - 1)
