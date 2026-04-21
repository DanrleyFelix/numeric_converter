from dataclasses import dataclass, field
from numbers import Number

from src.application.dto.command_entry import CommandEntryDTO, CommandLogEntryDTO


def _default_converter_fields() -> dict[str, str]:
    return {
        "decimal": "",
        "binary": "",
        "hexBE": "",
        "hexLE": "",
    }


def _default_command_variables() -> dict[str, Number]:
    return {"ANS": 0}


@dataclass(frozen=True)
class ConverterStateDTO:
    from_type: str = "decimal"
    fields: dict[str, str] = field(default_factory=_default_converter_fields)
    message: str | None = None


@dataclass(frozen=True)
class CommandContextDTO:
    active_line: str = ""
    history: list[CommandEntryDTO] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    variables: dict[str, Number] = field(default_factory=_default_command_variables)


@dataclass(frozen=True)
class ApplicationContextDTO:
    converter: ConverterStateDTO = field(default_factory=ConverterStateDTO)
    command: CommandContextDTO = field(default_factory=CommandContextDTO)
    key_panel_visible: bool = True


@dataclass(frozen=True)
class CommandLogDTO:
    entries: list[CommandLogEntryDTO] = field(default_factory=list)
