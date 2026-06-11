from __future__ import annotations

from typing import Any

from src.core.binary_workbench.context_overlays import (
    compact_binary_context_overlays,
)
from src.core.binary_workbench.legacy_overlays import discard_legacy_nop_overlays
from src.core.binary_workbench.version_overlays import (
    instructions_by_line_from_rows,
    without_blank_instruction_overlays,
)
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    BinaryWorkbenchViewPreferencesDTO,
    WindowSizeDTO,
)
from src.modules.utils import normalize_string_list, normalize_string_map


def _string_list_map(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): normalize_string_list(value) for key, value in raw.items()}


def _visible_columns(raw: object) -> dict[str, bool]:
    if not isinstance(raw, dict):
        return BinaryWorkbenchViewPreferencesDTO().visible_columns
    return {str(key): bool(value) for key, value in raw.items()}


def _view_preferences(raw: object) -> BinaryWorkbenchViewPreferencesDTO:
    if not isinstance(raw, dict):
        return BinaryWorkbenchViewPreferencesDTO()
    return BinaryWorkbenchViewPreferencesDTO(
        visible_columns=_visible_columns(raw.get("visible_columns")),
        decoded_text_tables=normalize_string_list(raw.get("decoded_text_tables")),
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
            )
        )
    return rows


def _row_payload(row: BinaryWorkbenchRowDTO) -> dict[str, str]:
    return {
        "offset": row.offsets.get("File", "0x00000000"),
        "instruction": row.instruction,
        "bytes_text": row.bytes_text,
    }


def _version_instructions_payload(version: BinaryWorkbenchVersionDTO) -> dict[str, str]:
    values = version.instructions_by_line or instructions_by_line_from_rows(
        version.rows,
    )
    return {
        str(line): instruction
        for line, instruction in sorted(values.items())
    }


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
    value = raw if isinstance(raw, int) else 2352
    return value if value in {2048, 2334, 2352} else 2352


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
    reference_offsets = _reference_offsets(raw)
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
        cpu_arch=str(raw.get("cpu_arch", "PSX - Mips R3000A")),
        read_mode=str(raw.get("read_mode", "auto")),
        reference_offsets=reference_offsets,
        reference_offset_bases=normalize_string_map(raw.get("reference_offset_bases")),
        labels=normalize_string_map(raw.get("labels")),
        equates=normalize_string_map(raw.get("equates")),
        variables=normalize_string_map(raw.get("variables")),
        symbol_offsets=_string_list_map(raw.get("symbol_offsets")),
        search_cache=_string_list_map(raw.get("search_cache")),
        internal_files=_internal_files(raw.get("internal_files")),
        lba_sector_size=_lba_sector_size(raw.get("lba_sector_size")),
        named_regions=normalize_string_list(raw.get("named_regions")),
        versions=_versions(raw.get("versions")),
        active_version_name=active_version_name,
        workspace_path=str(raw.get("workspace_path"))
        if isinstance(raw.get("workspace_path"), str)
        else None,
        module_paths=normalize_string_map(raw.get("module_paths")),
        module_directories=normalize_string_map(raw.get("module_directories")),
        module_checksums=normalize_string_map(raw.get("module_checksums")),
        last_open_offset=str(raw.get("last_open_offset", "0x00000000")),
        navigation_history=normalize_string_list(raw.get("navigation_history")),
        original_rows=[] if is_virtual_binary else _rows(raw.get("original_rows")),
        rows=[] if is_virtual_binary else _rows(raw.get("rows")),
        file_size=_positive_int(raw.get("file_size"), 0),
        original_file_size=_positive_int(raw.get("original_file_size"), 0),
        version_dirty=_bool(raw.get("version_dirty"), False)
        and bool(active_version_name or byte_overlays or instruction_overlays),
        byte_overlays=byte_overlays,
        instruction_overlays=instruction_overlays,
        view_preferences=_view_preferences(raw.get("view_preferences")),
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
                "lba_sector_size": tab.lba_sector_size,
                "named_regions": list(tab.named_regions),
                "versions": [
                    {
                        "name": version.name,
                        "rows": [_row_payload(row) for row in version.rows],
                        "instructions": {
                            **_version_instructions_payload(version),
                        },
                    }
                    for version in tab.versions
                ],
                "active_version_name": tab.active_version_name,
                "workspace_path": tab.workspace_path,
                "module_paths": dict(tab.module_paths),
                "module_directories": dict(tab.module_directories),
                "module_checksums": dict(tab.module_checksums),
                "last_open_offset": tab.last_open_offset,
                "navigation_history": list(tab.navigation_history),
                "file_size": tab.file_size,
                "original_file_size": tab.original_file_size,
                "version_dirty": tab.version_dirty,
                "byte_overlays": {} if _is_virtual_binary(tab) else dict(tab.byte_overlays),
                "instruction_overlays": {} if _is_virtual_binary(tab) else dict(tab.instruction_overlays),
                "original_rows": [] if _is_virtual_binary(tab) else [_row_payload(row) for row in tab.original_rows],
                "rows": [] if _is_virtual_binary(tab) else [_row_payload(row) for row in tab.rows],
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


def _reference_offsets(raw: dict[str, Any]) -> list[str]:
    values = normalize_string_list(raw.get("reference_offsets"))
    return values or ["File"]
