from dataclasses import dataclass
from typing import Any
from src.application.dto.formatting_context import FormattingOutputDTO


@dataclass(frozen=True)
class ConversionResultDTO:
    values: dict[str, Any]
    formatting: dict[str, FormattingOutputDTO]
    from_type: str
