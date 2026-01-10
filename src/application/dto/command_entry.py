from dataclasses import dataclass
from typing import Optional
from numbers import Number

from src.modules.utils import COLOR


@dataclass(frozen=True)
class CommandEntryDTO:
    input: str
    output: Optional[str]


@dataclass(frozen=True)
class CommandLogEntryDTO:
    input: str
    success: bool
    message: Optional[str] = None
    result: Optional[Number] = None
