from __future__ import annotations

from typing import Any

from src.core.binary_workbench.context_overlays import (
    compact_binary_context_overlays,
)
from src.core.binary_workbench.encoding_tables import encoding_table_from_payload
from src.core.binary_workbench.legacy_overlays import discard_legacy_nop_overlays
from src.core.binary_workbench.version_overlays import (
    instructions_by_line_from_rows,
    without_blank_instruction_overlays,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS,
    BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchEncodingTableDTO,
    BinaryWorkbenchOffsetRegionDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.modules.shared_dtos import WindowSizeDTO
from src.modules.utils import normalize_string_list, normalize_string_map


def _string_list_map(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): normalize_string_list(value) for key, value in raw.items()}


def _visible_columns(raw: object) -> dict[str, bool]:
    if not isinstance(raw, dict):
        return BinaryWorkbenchViewPreferencesDTO().visible_columns
    return {
        **BinaryWorkbenchViewPreferencesDTO().visible_columns,
        **{str(key): bool(value) for key, value in raw.items()},
    }


def _view_preferences(raw: object) -> BinaryWorkbenchViewPreferencesDTO:
    if not isinstance(raw, dict):
        return BinaryWorkbenchViewPreferencesDTO()
    enabled = raw.get("decoded_text_tables")
    return BinaryWorkbenchViewPreferencesDTO(
        visible_columns=_visible_columns(raw.get("visible_columns")),
        decoded_text_tables=(
            normalize_string_list(enabled)
            if isinstance(enabled, list)
            else BinaryWorkbenchViewPreferencesDTO().decoded_text_tables
        ),
    )


def _bool(raw: object, default: bool) -> bool:
    return raw if isinstance(raw, bool) else default


def _positive_int(raw: object, default: int) -> int:
    value = raw if isinstance(raw, int) else default
    return value if value > 0 else default


def _window_size(raw: object) -> WindowSizeDTO | None:
    if not isinstance(raw, dict):
        return None
    width = raw.get("width")
    height = raw.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    if width <= 0 or height <= 0:
        return None
    return WindowSizeDTO(width=width, height=height)


def _rows(raw: object) -> list[BinaryWorkbenchRowDTO]:
    if not isinstance(raw, list):
        return []
    rows: list[BinaryWorkbenchRowDTO] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        offsets = normalize_string_map(item.get("offsets"))
        if "offset" in item:
            offsets = {"File": _offset_hex(item.get("offset")), **offsets}
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=offsets,
                instruction=str(item.get("instruction", "")),
                bytes_text=str(item.get("bytes_text", "00 00 00 00")),
                original_instruction=str(item.get("original_instruction", "")),
                original_bytes_text=str(item.get("original_bytes_text", "")),
            )
        )
    return rows


def _row_payload(row: BinaryWorkbenchRowDTO) -> dict[str, object]:
    return {
        "offset": row.offsets.get("File", "0x00000000"),
        "offsets": dict(row.offsets),
        "instruction": row.instruction,
        "bytes_text": row.bytes_text,
        "original_instruction": row.original_instruction,
        "original_bytes_text": row.original_bytes_text,
    }


def _version_instructions_payload(version: BinaryWorkbenchVersionDTO) -> dict[str, str]:
    stored = version.instructions_by_line
    values = stored if isinstance(stored, dict) and stored else (
        instructions_by_line_from_rows(version.rows) or {}
    )
    return {
        str(line): instruction
        for line, instruction in sorted(values.items())
    }


def _encoding_tables(raw: object) -> list[BinaryWorkbenchEncodingTableDTO]:
    if not isinstance(raw, list):
        return []
    tables: list[BinaryWorkbenchEncodingTableDTO] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        table = encoding_table_from_payload(item.get("values"), item["name"])
        if table is not None:
            tables.append(table)
    return tables


def _offset_regions(raw: object) -> list[BinaryWorkbenchOffsetRegionDTO]:
    if not isinstance(raw, list):
        return []
    regions: list[BinaryWorkbenchOffsetRegionDTO] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        offset = item.get("offset")
        if not isinstance(offset, int) or offset < 0:
            continue
        details = item.get("details")
        regions.append(BinaryWorkbenchOffsetRegionDTO(
            name=item["name"],
            offset=offset,
            details=details if isinstance(details, str) else "",
        ))
    return regions


def _internal_files(raw: object) -> list[BinaryWorkbenchInternalFileDTO]:
    if not isinstance(raw, list):
        return []
    files: list[BinaryWorkbenchInternalFileDTO] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        start_lba = item.get("start_lba")
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(start_lba, int):
            continue
        files.append(BinaryWorkbenchInternalFileDTO(name=name, start_lba=start_lba))
    return files


def _versions(raw: object) -> list[BinaryWorkbenchVersionDTO]:
    if not isinstance(raw, list):
        return []
    versions: list[BinaryWorkbenchVersionDTO] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            continue
        versions.append(
            BinaryWorkbenchVersionDTO(
                name=name,
                rows=_rows(item.get("rows")),
                instruction_overlays=_instruction_overlays(item.get("instructions")),
                instructions_by_line=_instructions_by_line(item.get("instructions")),
            )
        )
    return versions


def _instructions_by_line(raw: object) -> dict[int, str]:
    if not isinstance(raw, dict):
        return {}
    values: dict[int, str] = {}
    for key, value in raw.items():
        try:
            line = int(key)
        except (TypeError, ValueError):
            continue
        if line >= 0:
            values[line] = str(value)
    return values


def _instruction_overlays(raw: object) -> dict[str, str]:
    if isinstance(raw, dict):
        return {
            _offset_hex(key): str(value)
            for key, value in raw.items()
            if _is_offset_key(key)
        }
    if not isinstance(raw, list):
        return {}
    overlays: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        offset = _int_offset(item.get("offset"))
        instruction = item.get("instruction")
        if offset is None or not isinstance(instruction, str):
            continue
        overlays[f"0x{offset:08X}"] = instruction
    return overlays


def _is_offset_key(raw: object) -> bool:
    return not isinstance(raw, int) and str(raw).lower().startswith("0x")


def _lba_sector_size(raw: object) -> int:
    value = raw if isinstance(raw, int) else BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
    return (
        value
        if value in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS
        else BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
    )


def _int_offset(raw: object) -> int | None:
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, str):
        try:
            value = int(raw, 0)
        except ValueError:
            return None
        return value if value >= 0 else None
    return None


def _offset_hex(raw: object) -> str:
    value = _int_offset(raw)
    return f"0x{value:08X}" if value is not None else str(raw)


def _tab_context(raw: object) -> BinaryWorkbenchTabContextDTO | None:
    if not isinstance(raw, dict):
        return None
    tab_id = raw.get("tab_id")
    kind = raw.get("kind")
    display_name = raw.get("display_name")
    if not all(isinstance(value, str) and value for value in (tab_id, kind, display_name)):
        return None
    source_path = raw.get("source_path")
    is_virtual_binary = kind == "binary"
    uses_virtual_rows = kind in {"binary", "internal"}
    reference_offsets = _reference_offsets(raw)
    reference_offset_bases = normalize_string_map(raw.get("reference_offset_bases"))
    view_preferences = _view_preferences(raw.get("view_preferences"))
    if kind == "internal":
        reference_offsets = [
            name for name in reference_offsets if name != "Binary"
        ]
        reference_offset_bases.pop("Binary", None)
        view_preferences = BinaryWorkbenchViewPreferencesDTO(
            visible_columns={
                name: visible
                for name, visible in view_preferences.visible_columns.items()
                if name != "Binary"
            },
            decoded_text_tables=list(view_preferences.decoded_text_tables),
        )
    internal_files = _internal_files(raw.get("internal_files"))
    internal_file_start_lba = _int_offset(raw.get("internal_file_start_lba"))
    internal_parent_tab_id = raw.get("internal_parent_tab_id")
    if internal_file_start_lba is None and kind == "internal":
        selected = next((item for item in internal_files if item.name == display_name), None)
        internal_file_start_lba = selected.start_lba if selected is not None else None
    active_version_name = str(raw.get("active_version_name")) if isinstance(raw.get("active_version_name"), str) else None
    byte_overlays, instruction_overlays = (
        ({}, {})
        if is_virtual_binary
        else without_blank_instruction_overlays(
            normalize_string_map(raw.get("byte_overlays")),
            normalize_string_map(raw.get("instruction_overlays")),
        )
    )
    return discard_legacy_nop_overlays(compact_binary_context_overlays(BinaryWorkbenchTabContextDTO(
        tab_id=tab_id,
        kind=kind,
        display_name=display_name,
        source_path=str(source_path) if isinstance(source_path, str) else None,
        cpu_arch=str(
            raw.get("cpu_arch", BINARY_WORKBENCH_PSX_MIPS_R3000A_DISPLAY_NAME)
        ),
        read_mode=str(raw.get("read_mode", "auto")),
        reference_offsets=reference_offsets,
        reference_offset_bases=reference_offset_bases,
        labels=normalize_string_map(raw.get("labels")),
        equates=normalize_string_map(raw.get("equates")),
        variables=normalize_string_map(raw.get("variables")),
        symbol_offsets=_string_list_map(raw.get("symbol_offsets")),
        search_cache=_string_list_map(raw.get("search_cache")),
        internal_files=internal_files,
        internal_file_start_lba=internal_file_start_lba,
        internal_parent_tab_id=(
            internal_parent_tab_id
            if isinstance(internal_parent_tab_id, str) and internal_parent_tab_id
            else None
        ),
        internal_parent_byte_overlays=normalize_string_map(
            raw.get("internal_parent_byte_overlays")
        ),
        lba_sector_size=_lba_sector_size(raw.get("lba_sector_size")),
        named_regions=normalize_string_list(raw.get("named_regions")),
        offset_regions=_offset_regions(raw.get("offset_regions")),
        encoding_tables=_encoding_tables(raw.get("encoding_tables")),
        versions=_versions(raw.get("versions")),
        active_version_name=active_version_name,
        workspace_path=str(raw.get("workspace_path"))
        if isinstance(raw.get("workspace_path"), str)
        else None,
        module_paths=normalize_string_map(raw.get("module_paths")),
        module_directories=normalize_string_map(raw.get("module_directories")),
        module_checksums=normalize_string_map(raw.get("module_checksums")),
        custom_commands=_string_list_map(raw.get("custom_commands")),
        last_open_offset=str(raw.get("last_open_offset", "0x00000000")),
        navigation_history=normalize_string_list(raw.get("navigation_history")),
        original_rows=[] if uses_virtual_rows else _rows(raw.get("original_rows")),
        rows=[] if uses_virtual_rows else _rows(raw.get("rows")),
        file_size=_positive_int(raw.get("file_size"), 0),
        original_file_size=_positive_int(raw.get("original_file_size"), 0),
        version_dirty=_bool(raw.get("version_dirty"), False)
        and bool(active_version_name or byte_overlays or instruction_overlays),
        byte_overlays=byte_overlays,
        instruction_overlays=instruction_overlays,
        view_preferences=view_preferences,
    )))


def binary_workbench_state_from_payload(raw: dict[str, Any]) -> BinaryWorkbenchStateDTO:
    tabs = [tab for item in raw.get("tabs", []) if (tab := _tab_context(item)) is not None]
    active_tab_id = raw.get("active_tab_id")
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active_tab_id if isinstance(active_tab_id, str) else None,
        share_view_preferences=bool(raw.get("share_view_preferences", False)),
        directories={
            **BinaryWorkbenchStateDTO().directories,
            **normalize_string_map(raw.get("directories")),
        },
        window_size=_window_size(raw.get("window_size")),
    )


def binary_workbench_state_to_payload(
    state: BinaryWorkbenchStateDTO,
) -> dict[str, Any]:
    tabs = [compact_binary_context_overlays(tab) for tab in state.tabs]
    return {
        "tabs": [
            {
                "tab_id": tab.tab_id,
                "kind": tab.kind,
                "display_name": tab.display_name,
                "source_path": tab.source_path,
                "cpu_arch": tab.cpu_arch,
                "read_mode": tab.read_mode,
                "reference_offsets": list(tab.reference_offsets),
                "reference_offset_bases": {k: v for k, v in dict(tab.reference_offset_bases).items() if not (k == "File" and v == "0x00000000")},
                "labels": dict(tab.labels),
                "equates": dict(tab.equates),
                "variables": dict(tab.variables),
                "symbol_offsets": {
                    key: list(value) for key, value in tab.symbol_offsets.items()
                },
                "search_cache": {
                    key: list(value) for key, value in tab.search_cache.items()
                },
                "internal_files": [
                    {"name": item.name, "start_lba": item.start_lba}
                    for item in tab.internal_files
                ],
                "internal_file_start_lba": tab.internal_file_start_lba,
                "internal_parent_tab_id": tab.internal_parent_tab_id,
                "internal_parent_byte_overlays": dict(
                    tab.internal_parent_byte_overlays
                ),
                "lba_sector_size": tab.lba_sector_size,
                "named_regions": list(tab.named_regions),
                "offset_regions": [
                    {"name": item.name, "offset": item.offset, "details": item.details}
                    for item in tab.offset_regions
                ],
                "encoding_tables": [
                    {
                        "name": table.name,
                        "values": {f"0x{byte:02X}": text for byte, text in table.values.items()},
                    }
                    for table in tab.encoding_tables
                ],
                "versions": [
                    {
                        "name": version.name,
                        "rows": [_row_payload(row) for row in version.rows],
                        "instructions": _version_instructions_payload(version),
                    }
                    for version in tab.versions
                ],
                "active_version_name": tab.active_version_name,
                "workspace_path": tab.workspace_path,
                "module_paths": dict(tab.module_paths),
                "module_directories": dict(tab.module_directories),
                "module_checksums": dict(tab.module_checksums),
                "custom_commands": {
                    key: list(value)
                    for key, value in tab.custom_commands.items()
                },
                "last_open_offset": tab.last_open_offset,
                "navigation_history": list(tab.navigation_history),
                "file_size": tab.file_size,
                "original_file_size": tab.original_file_size,
                "version_dirty": tab.version_dirty,
                "byte_overlays": {} if _is_virtual_binary(tab) else dict(tab.byte_overlays),
                "instruction_overlays": {} if _is_virtual_binary(tab) else dict(tab.instruction_overlays),
                "original_rows": [] if _uses_virtual_rows(tab) else [_row_payload(row) for row in tab.original_rows],
                "rows": [] if _uses_virtual_rows(tab) else [_row_payload(row) for row in tab.rows],
                "view_preferences": {
                    "visible_columns": dict(tab.view_preferences.visible_columns),
                    "decoded_text_tables": list(tab.view_preferences.decoded_text_tables),
                },
            }
            for tab in tabs
        ],
        "active_tab_id": state.active_tab_id,
        "share_view_preferences": state.share_view_preferences,
        "directories": dict(state.directories),
        "window_size": {
            "width": state.window_size.width,
            "height": state.window_size.height,
        }
        if state.window_size is not None
        else None,
    }


def _is_virtual_binary(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return tab.kind == "binary"


def _uses_virtual_rows(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return tab.kind in {"binary", "internal"}


def _reference_offsets(raw: dict[str, Any]) -> list[str]:
    values = normalize_string_list(raw.get("reference_offsets"))
    return values or ["File"]
