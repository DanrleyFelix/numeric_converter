from __future__ import annotations

from typing import Any

from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    BinaryWorkbenchViewPreferencesDTO,
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
        group_bytes=_group_bytes(raw.get("group_bytes")),
    )


def _group_bytes(raw: object) -> int:
    value = raw if isinstance(raw, int) else 1
    return value if value in {1, 2, 4} else 1


def _positive_int(raw: object, default: int) -> int:
    value = raw if isinstance(raw, int) else default
    return value if value > 0 else default


def _rows(raw: object) -> list[BinaryWorkbenchRowDTO]:
    if not isinstance(raw, list):
        return []
    rows: list[BinaryWorkbenchRowDTO] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=normalize_string_map(item.get("offsets")),
                instruction=str(item.get("instruction", "")),
                bytes_text=str(item.get("bytes_text", "00 00 00 00")),
            )
        )
    return rows


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
        versions.append(BinaryWorkbenchVersionDTO(name=name, rows=_rows(item.get("rows"))))
    return versions


def _tab_context(raw: object) -> BinaryWorkbenchTabContextDTO | None:
    if not isinstance(raw, dict):
        return None
    tab_id = raw.get("tab_id")
    kind = raw.get("kind")
    display_name = raw.get("display_name")
    if not all(isinstance(value, str) and value for value in (tab_id, kind, display_name)):
        return None
    source_path = raw.get("source_path")
    is_virtual_binary = kind == "binary" and raw.get("read_mode") != "assembly"
    reference_offsets = _reference_offsets(raw)
    return BinaryWorkbenchTabContextDTO(
        tab_id=tab_id,
        kind=kind,
        display_name=display_name,
        source_path=str(source_path) if isinstance(source_path, str) else None,
        cpu_arch=str(raw.get("cpu_arch", "PSX - Mips R3000A")),
        read_mode=str(raw.get("read_mode", "auto")),
        navigation_mode=str(raw.get("navigation_mode", "Offset")),
        reference_offsets=reference_offsets,
        reference_offset_bases={
            "File": "0x00000000",
            **normalize_string_map(raw.get("reference_offset_bases")),
        },
        labels=normalize_string_map(raw.get("labels")),
        equates=normalize_string_map(raw.get("equates")),
        variables=normalize_string_map(raw.get("variables")),
        symbol_offsets=_string_list_map(raw.get("symbol_offsets")),
        search_cache=_string_list_map(raw.get("search_cache")),
        internal_files=_internal_files(raw.get("internal_files")),
        named_regions=normalize_string_list(raw.get("named_regions")),
        versions=_versions(raw.get("versions")),
        active_version_name=str(raw.get("active_version_name"))
        if isinstance(raw.get("active_version_name"), str)
        else None,
        last_open_offset=str(raw.get("last_open_offset", "0x00000000")),
        navigation_history=normalize_string_list(raw.get("navigation_history")),
        original_rows=[] if is_virtual_binary else _rows(raw.get("original_rows")),
        rows=[] if is_virtual_binary else _rows(raw.get("rows")),
        file_size=_positive_int(raw.get("file_size"), 0),
        block_size=_positive_int(raw.get("block_size"), 2048),
        cache_max_blocks=_positive_int(raw.get("cache_max_blocks"), 8000),
        byte_overlays=normalize_string_map(raw.get("byte_overlays")),
        view_preferences=_view_preferences(raw.get("view_preferences")),
    )


def binary_workbench_state_from_payload(raw: dict[str, Any]) -> BinaryWorkbenchStateDTO:
    tabs = [tab for item in raw.get("tabs", []) if (tab := _tab_context(item)) is not None]
    active_tab_id = raw.get("active_tab_id")
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active_tab_id if isinstance(active_tab_id, str) else None,
        share_view_preferences=bool(raw.get("share_view_preferences", False)),
        recent_files=normalize_string_list(raw.get("recent_files")),
        directories={
            **BinaryWorkbenchStateDTO().directories,
            **normalize_string_map(raw.get("directories")),
        },
    )


def binary_workbench_state_to_payload(
    state: BinaryWorkbenchStateDTO,
) -> dict[str, Any]:
    return {
        "tabs": [
            {
                "tab_id": tab.tab_id,
                "kind": tab.kind,
                "display_name": tab.display_name,
                "source_path": tab.source_path,
                "cpu_arch": tab.cpu_arch,
                "read_mode": tab.read_mode,
                "navigation_mode": tab.navigation_mode,
                "reference_offsets": list(tab.reference_offsets),
                "reference_offset_bases": dict(tab.reference_offset_bases),
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
                "named_regions": list(tab.named_regions),
                "versions": [
                    {
                        "name": version.name,
                        "rows": [
                            {
                                "offsets": dict(row.offsets),
                                "instruction": row.instruction,
                                "bytes_text": row.bytes_text,
                            }
                            for row in version.rows
                        ],
                    }
                    for version in tab.versions
                ],
                "active_version_name": tab.active_version_name,
                "last_open_offset": tab.last_open_offset,
                "navigation_history": list(tab.navigation_history),
                "file_size": tab.file_size,
                "block_size": tab.block_size,
                "cache_max_blocks": tab.cache_max_blocks,
                "byte_overlays": dict(tab.byte_overlays),
                "original_rows": [] if _is_virtual_binary(tab) else [
                    {
                        "offsets": dict(row.offsets),
                        "instruction": row.instruction,
                        "bytes_text": row.bytes_text,
                    }
                    for row in tab.original_rows
                ],
                "rows": [] if _is_virtual_binary(tab) else [
                    {
                        "offsets": dict(row.offsets),
                        "instruction": row.instruction,
                        "bytes_text": row.bytes_text,
                    }
                    for row in tab.rows
                ],
                "view_preferences": {
                    "visible_columns": dict(tab.view_preferences.visible_columns),
                    "decoded_text_tables": list(tab.view_preferences.decoded_text_tables),
                    "group_bytes": tab.view_preferences.group_bytes,
                },
            }
            for tab in state.tabs
        ],
        "active_tab_id": state.active_tab_id,
        "share_view_preferences": state.share_view_preferences,
        "recent_files": list(state.recent_files),
        "directories": dict(state.directories),
    }


def _is_virtual_binary(tab: BinaryWorkbenchTabContextDTO) -> bool:
    return tab.kind == "binary" and tab.read_mode != "assembly"


def _reference_offsets(raw: dict[str, Any]) -> list[str]:
    values = normalize_string_list(raw.get("reference_offsets"))
    if not values:
        return ["File"]
    if values == ["File", "RAM", "SLUS"] and not raw.get("reference_offset_bases"):
        return ["File"]
    return values
