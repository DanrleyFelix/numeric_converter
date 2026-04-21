from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CommandEntryDTO:
    input: str
    output: Optional[str]
