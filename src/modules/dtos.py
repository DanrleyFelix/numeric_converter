from dataclasses import dataclass, field
from numbers import Number
from typing import Any


def _default_visible_columns() -> dict[str, bool]:
    return {
        "File": True,
        "RAM": True,
        "SLUS": False,
        "Instruction": True,
        "Bytes": True,
    }


def _default_converter_fields() -> dict[str, str]:
    return {"decimal": "", "binary": "", "hexBE": "", "hexLE": ""}


def _default_command_variables() -> dict[str, Number]:
    return {"ANS": 0}


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
class CommandEntryDTO:
    input: str
    output: str | None


@dataclass(frozen=True)
class CommandRenderResultDTO:
    lines: list[str]
    color: str
    message: str | None = None


@dataclass(frozen=True)
class WindowSizeDTO:
    width: int
    height: int


@dataclass(frozen=True)
class BinaryWorkbenchViewPreferencesDTO:
    visible_columns: dict[str, bool] = field(default_factory=_default_visible_columns)
    decoded_text_tables: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BinaryWorkbenchRowDTO:
    offsets: dict[str, str] = field(default_factory=dict)
    instruction: str = ""
    bytes_text: str = "00 00 00 00"


@dataclass(frozen=True)
class BinaryWorkbenchTabContextDTO:
    tab_id: str
    kind: str
    display_name: str
    source_path: str | None = None
    cpu_arch: str = "PSX - Mips R3000A"
    navigation_mode: str = "Offset"
    reference_offsets: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    internal_files: list[str] = field(default_factory=list)
    named_regions: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    last_open_offset: str = "0x00000000"
    navigation_history: list[str] = field(default_factory=list)
    rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    view_preferences: BinaryWorkbenchViewPreferencesDTO = field(
        default_factory=BinaryWorkbenchViewPreferencesDTO
    )


@dataclass(frozen=True)
class BinaryWorkbenchStateDTO:
    tabs: list[BinaryWorkbenchTabContextDTO] = field(default_factory=list)
    active_tab_id: str | None = None
    share_view_preferences: bool = False


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
    binary_workbench: BinaryWorkbenchStateDTO = field(
        default_factory=BinaryWorkbenchStateDTO
    )
    key_panel_visible: bool = True
    auto_convert_enabled: bool = False
    window_sizes: dict[str, WindowSizeDTO] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceStateDTO:
    context: ApplicationContextDTO = field(default_factory=ApplicationContextDTO)
