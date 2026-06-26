from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)


def offset_from_hex(value: str) -> int:
    try:
        return int(value, 16)
    except ValueError:
        return 0


def default_editor_kind(context: BinaryWorkbenchTabContextDTO) -> str:
    if context.kind in {BINARY_WORKBENCH_TAB_KIND.ASSEMBLY, BINARY_WORKBENCH_TAB_KIND.SCRATCH}:
        return BINARY_WORKBENCH_TEXT.INSTRUCTION
    return BINARY_WORKBENCH_TEXT.BYTES
