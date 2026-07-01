from dataclasses import dataclass, field

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_ANSI_TABLE_NAME,
    BINARY_WORKBENCH_BYTE_GROUP_OPTIONS,
    BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE,
    BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS,
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)
from src.modules.binary_workbench_resource_dtos import (
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchLbaFilesystemDTO,
    BinaryWorkbenchOffsetRegionDTO,
    BinaryWorkbenchSymbolsDTO,
)
from src.modules.shared_dtos import WindowSizeDTO


def _default_visible_columns() -> dict[str, bool]:
    return {
        "File": True,
        "Editor (Assembly Code)": True,
        "Raw Instructions": True,
        "Decoded Text": False,
        "Bytes": True,
    }


def _default_decoded_text_tables() -> list[str]:
    return [BINARY_WORKBENCH_ANSI_TABLE_NAME]


def _default_binary_workbench_directories() -> dict[str, str]:
    return {
        "open_file": "",
        "open_binary": "",
        "open_assembly": "",
        "save_file": "",
        "save_assembly": "",
        "lba_filesystem": "",
        "symbols": "",
        "versions": "",
        "encoding_tables": "",
        "offset_regions": "",
        "commands": "",
    }


@dataclass(frozen=True)
class BinaryWorkbenchViewPreferencesDTO:
    visible_columns: dict[str, bool] = field(default_factory=_default_visible_columns)
    decoded_text_tables: list[str] = field(default_factory=_default_decoded_text_tables)


@dataclass(frozen=True)
class BinaryWorkbenchEditRulesDTO:
    allow_byte_shift: bool = False
    allow_editor_edit: bool = True
    allow_free_edit_after_original_end: bool = True


def _default_assembly_edit_rules() -> BinaryWorkbenchEditRulesDTO:
    return BinaryWorkbenchEditRulesDTO(
        allow_byte_shift=True,
        allow_editor_edit=True,
        allow_free_edit_after_original_end=True,
    )


@dataclass(frozen=True)
class BinaryWorkbenchPreferencesDTO:
    group_bytes: int = BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[0]
    uppercase_bytes: bool = True
    uppercase_instructions: bool = True
    block_size: int = BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE
    cache_max_blocks: int = BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS
    selection_limit_bytes: int = 2 * 1024 * 1024
    binary_edit_rules: BinaryWorkbenchEditRulesDTO = field(default_factory=BinaryWorkbenchEditRulesDTO)
    assembly_edit_rules: BinaryWorkbenchEditRulesDTO = field(default_factory=_default_assembly_edit_rules)


@dataclass(frozen=True)
class BinaryWorkbenchRowDTO:
    offsets: dict[str, str] = field(default_factory=dict)
    instruction: str = ""
    bytes_text: str = "00 00 00 00"
    original_instruction: str = ""
    original_bytes_text: str = ""


@dataclass(frozen=True)
class BinaryWorkbenchVersionDTO:
    name: str
    rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    instruction_overlays: dict[str, str] = field(default_factory=dict)
    instructions_by_line: dict[int, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    symbols_loaded: bool = False


@dataclass(frozen=True)
class BinaryWorkbenchTabContextDTO:
    tab_id: str
    kind: str
    display_name: str
    source_path: str | None = None
    cpu_arch: str = BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME
    read_mode: str = "auto"
    reference_offsets: list[str] = field(default_factory=list)
    reference_offset_bases: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    symbol_offsets: dict[str, list[str]] = field(default_factory=dict)
    search_cache: dict[str, list[str]] = field(default_factory=dict)
    internal_files: list[BinaryWorkbenchInternalFileDTO] = field(default_factory=list)
    internal_file_start_lba: int | None = None
    internal_parent_tab_id: str | None = None
    internal_parent_byte_overlays: dict[str, str] = field(default_factory=dict)
    keep_workspace_resources: bool = False
    lba_sector_size: int = BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
    named_regions: list[str] = field(default_factory=list)
    offset_regions: list[BinaryWorkbenchOffsetRegionDTO] = field(default_factory=list)
    offset_regions_loaded: bool = False
    encoding_tables: list[BinaryWorkbenchEncodingTableDTO] = field(default_factory=list)
    versions: list[BinaryWorkbenchVersionDTO] = field(default_factory=list)
    active_version_name: str | None = None
    workspace_path: str | None = None
    module_paths: dict[str, str] = field(default_factory=dict)
    module_directories: dict[str, str] = field(default_factory=dict)
    module_checksums: dict[str, str] = field(default_factory=dict)
    custom_commands: dict[str, list[str]] = field(default_factory=dict)
    last_open_offset: str = "0x00000000"
    navigation_history: list[str] = field(default_factory=list)
    original_rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    rows: list[BinaryWorkbenchRowDTO] = field(default_factory=list)
    file_size: int = 0
    original_file_size: int = 0
    version_dirty: bool = False
    byte_overlays: dict[str, str] = field(default_factory=dict)
    instruction_overlays: dict[str, str] = field(default_factory=dict)
    view_preferences: BinaryWorkbenchViewPreferencesDTO = field(default_factory=BinaryWorkbenchViewPreferencesDTO)


@dataclass(frozen=True)
class BinaryWorkbenchStateDTO:
    tabs: list[BinaryWorkbenchTabContextDTO] = field(default_factory=list)
    active_tab_id: str | None = None
    share_view_preferences: bool = False
    directories: dict[str, str] = field(default_factory=_default_binary_workbench_directories)
    commands_by_arch: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    encoding_tables: list[BinaryWorkbenchEncodingTableDTO] = field(default_factory=list)
    window_size: WindowSizeDTO | None = None
