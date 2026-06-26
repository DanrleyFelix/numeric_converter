from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditorCommand:
    name: str
    instructions: tuple[str, ...]

    @property
    def slash_name(self) -> str:
        return f"/{self.name}"
