from dataclasses import dataclass, field
from typing import Any


def _default_converter_fields() -> dict[str, str]:
    return {"decimal": "", "binary": "", "hexBE": "", "hexLE": ""}


@dataclass(frozen=True)
class FormattingOutputDTO:
    group_size: int = 0
    zero_pad: bool = False


@dataclass(frozen=True)
class ConversionResultDTO:
    values: dict[str, Any]
    formatting: dict[str, FormattingOutputDTO]
    from_type: str


@dataclass(frozen=True)
class ConverterStateDTO:
    from_type: str = "decimal"
    fields: dict[str, str] = field(default_factory=_default_converter_fields)
    message: str | None = None
