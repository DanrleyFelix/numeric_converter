from pathlib import Path

from src.core.binary_workbench.resource_identity import file_resource_identifiers
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE,
    BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO, BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT


def state_payload(state: BinaryWorkbenchStateDTO) -> dict[str, object]:
    return {
        "tabs": state.tabs,
        "active_tab_id": state.active_tab_id,
        "share_view_preferences": state.share_view_preferences,
        "directories": dict(state.directories),
        "window_size": state.window_size,
    }


def lba_sector_size(value: int) -> int:
    return (
        value
        if value in BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS
        else BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
    )


def tab_text(value: str) -> str:
    if len(value) <= BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS:
        return value
    return f"{value[:BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS]}..."


def rows_to_bytes(rows: list[BinaryWorkbenchRowDTO]) -> bytes:
    return b"".join(bytes.fromhex(row.bytes_text.replace(" ", "")) for row in rows)
