from __future__ import annotations

from typing import Any

from src.modules.dtos import (
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchViewPreferencesDTO,
)
from src.modules.utils import normalize_string_list, normalize_string_map


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


def _tab_context(raw: object) -> BinaryWorkbenchTabContextDTO | None:
    if not isinstance(raw, dict):
        return None
    tab_id = raw.get("tab_id")
    kind = raw.get("kind")
    display_name = raw.get("display_name")
    if not all(isinstance(value, str) and value for value in (tab_id, kind, display_name)):
        return None
    source_path = raw.get("source_path")
    return BinaryWorkbenchTabContextDTO(
        tab_id=tab_id,
        kind=kind,
        display_name=display_name,
        source_path=str(source_path) if isinstance(source_path, str) else None,
        cpu_arch=str(raw.get("cpu_arch", "PSX - Mips R3000A")),
        navigation_mode=str(raw.get("navigation_mode", "Offset")),
        reference_offsets=normalize_string_list(raw.get("reference_offsets")),
        labels=normalize_string_map(raw.get("labels")),
        equates=normalize_string_map(raw.get("equates")),
        variables=normalize_string_map(raw.get("variables")),
        internal_files=normalize_string_list(raw.get("internal_files")),
        named_regions=normalize_string_list(raw.get("named_regions")),
        versions=normalize_string_list(raw.get("versions")),
        last_open_offset=str(raw.get("last_open_offset", "0x00000000")),
        navigation_history=normalize_string_list(raw.get("navigation_history")),
        rows=_rows(raw.get("rows")),
        view_preferences=_view_preferences(raw.get("view_preferences")),
    )


def binary_workbench_state_from_payload(raw: dict[str, Any]) -> BinaryWorkbenchStateDTO:
    tabs = [tab for item in raw.get("tabs", []) if (tab := _tab_context(item)) is not None]
    active_tab_id = raw.get("active_tab_id")
    return BinaryWorkbenchStateDTO(
        tabs=tabs,
        active_tab_id=active_tab_id if isinstance(active_tab_id, str) else None,
        share_view_preferences=bool(raw.get("share_view_preferences", False)),
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
                "navigation_mode": tab.navigation_mode,
                "reference_offsets": list(tab.reference_offsets),
                "labels": dict(tab.labels),
                "equates": dict(tab.equates),
                "variables": dict(tab.variables),
                "internal_files": list(tab.internal_files),
                "named_regions": list(tab.named_regions),
                "versions": list(tab.versions),
                "last_open_offset": tab.last_open_offset,
                "navigation_history": list(tab.navigation_history),
                "rows": [
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
                },
            }
            for tab in state.tabs
        ],
        "active_tab_id": state.active_tab_id,
        "share_view_preferences": state.share_view_preferences,
    }
