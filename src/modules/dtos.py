from dataclasses import dataclass, field
from numbers import Number
from typing import Any


def _default_visible_columns() -> dict[str, bool]:
    return {
        "File": True,
        "Instruction": True,
        "Bytes": True,
    }


def _default_binary_workbench_directories() -> dict[str, str]:
    return {
        "open_file": "",
        "open_binary": "",
        "open_assembly": "",
        "save_file": "",
        "save_assembly": "",
        "lba_filesystem": "",
        "memory_regions": "",
        "symbols": "",
        "versions": "",
        "encoding_tables": "",
    }


def _default_converter_fields() -> dict[str, str]:
    return {"decimal": "", "binary": "", "hexBE": "", "hexLE": ""}


def _default_command_variables() -> dict[str, Number]:
    return {"ANS": 0}


def _default_formatter_preferences() -> dict[str, "FormattingOutputDTO"]:
    return {
        "decimal": FormattingOutputDTO(4, True),
        "binary": FormattingOutputDTO(4, True),
        "hexBE": FormattingOutputDTO(2, True),
        "hexLE": FormattingOutputDTO(2, True),
    }


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
class BinaryWorkbenchPreferencesDTO:
    group_bytes: int = 1
    uppercase_bytes: bool = True
    uppercase_instructions: bool = True
    block_size: int = 2048
    cache_max_blocks: int = 8000


@dataclass(frozen=True)
class BinaryWorkbenchRowDTO:
    offsets: dict[str, str] = field(default_factory=dict)
    instruction: str = ""
    bytes_text: str = "00 00 00 00"


@dataclass(frozen=True)
class BinaryWorkbenchInternalFileDTO:
    name: str
    start_lba: int


@dataclass(frozen=True)
class BinaryWorkbenchMemoryRegionDTO:
    name: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class BinaryWorkbenchVersionDTO:
    name: str
    rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    instruction_overlays: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BinaryWorkbenchLbaFilesystemDTO:
    name: str
    file_identifiers: list[str] = field(default_factory=list)
    sector_size: int = 2352
    internal_files: list[BinaryWorkbenchInternalFileDTO] = field(default_factory=list)


@dataclass(frozen=True)
class BinaryWorkbenchSymbolsDTO:
    name: str
    file_identifiers: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BinaryWorkbenchTabContextDTO:
    tab_id: str
    kind: str
    display_name: str
    source_path: str | None = None
    cpu_arch: str = "PSX - Mips R3000A"
    read_mode: str = "auto"
    reference_offsets: list[str] = field(default_factory=list)
    reference_offset_bases: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    symbol_offsets: dict[str, list[str]] = field(default_factory=dict)
    search_cache: dict[str, list[str]] = field(default_factory=dict)
    internal_files: list[BinaryWorkbenchInternalFileDTO] = field(default_factory=list)
    lba_sector_size: int = 2352
    named_regions: list[str] = field(default_factory=list)
    memory_regions: list[BinaryWorkbenchMemoryRegionDTO] = field(default_factory=list)
    versions: list[BinaryWorkbenchVersionDTO] = field(default_factory=list)
    active_version_name: str | None = None
    workspace_path: str | None = None
    module_paths: dict[str, str] = field(default_factory=dict)
    module_directories: dict[str, str] = field(default_factory=dict)
    module_checksums: dict[str, str] = field(default_factory=dict)
    last_open_offset: str = "0x00000000"
    navigation_history: list[str] = field(default_factory=list)
    original_rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    file_size: int = 0
    version_dirty: bool = False
    byte_overlays: dict[str, str] = field(default_factory=dict)
    instruction_overlays: dict[str, str] = field(default_factory=dict)
    view_preferences: BinaryWorkbenchViewPreferencesDTO = field(
        default_factory=BinaryWorkbenchViewPreferencesDTO
    )


@dataclass(frozen=True)
class BinaryWorkbenchStateDTO:
    tabs: list[BinaryWorkbenchTabContextDTO] = field(default_factory=list)
    active_tab_id: str | None = None
    share_view_preferences: bool = False
    directories: dict[str, str] = field(default_factory=_default_binary_workbench_directories)
    window_size: WindowSizeDTO | None = None


@dataclass(frozen=True)
class ProgramContextDTO:
    recent_files: list[str] = field(default_factory=list)
    last_binary_workspaces: dict[str, str] = field(default_factory=dict)


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
    window_sizes: dict[str, WindowSizeDTO] = field(default_factory=dict)


@dataclass(frozen=True)
class NumericWorkbenchPreferencesDTO:
    formatters: dict[str, FormattingOutputDTO] = field(
        default_factory=_default_formatter_preferences
    )
    key_panel_visible: bool = True
    auto_convert_enabled: bool = False


@dataclass(frozen=True)
class WorkspaceStateDTO:
    context: ApplicationContextDTO = field(default_factory=ApplicationContextDTO)
