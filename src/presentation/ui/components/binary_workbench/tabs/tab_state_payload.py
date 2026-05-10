from pathlib import Path

from src.core.binary_workbench.resource_identity import file_resource_identifiers
from src.modules.dtos import BinaryWorkbenchRowDTO, BinaryWorkbenchStateDTO, BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT


def state_payload(state: BinaryWorkbenchStateDTO) -> dict[str, object]:
    return {
        "tabs": state.tabs,
        "active_tab_id": state.active_tab_id,
        "share_view_preferences": state.share_view_preferences,
        "recent_files": list(state.recent_files),
        "directories": dict(state.directories),
        "lba_filesystems": list(state.lba_filesystems),
        "symbols": list(state.symbols),
    }


def current_identifiers(context: BinaryWorkbenchTabContextDTO) -> list[str]:
    path = Path(context.source_path) if context.source_path else None
    return file_resource_identifiers(path, context.display_name)


def lba_sector_size(value: int) -> int:
    return value if value in {2048, 2334, 2352} else 2352


def tab_text(value: str) -> str:
    if len(value) <= BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS:
        return value
    return f"{value[: BINARY_WORKBENCH_LAYOUT.TAB_MAX_CHARACTERS - 3]}..."


def rows_to_bytes(rows: list[BinaryWorkbenchRowDTO]) -> bytes:
    return b"".join(bytes.fromhex(row.bytes_text.replace(" ", "")) for row in rows)
